import re
import logging
from typing import List, Dict, Any, AsyncGenerator, Tuple
from datetime import date
from app.core.database import get_supabase_client
from app.services.embeddings import embedding_service
from app.services.llm.client import get_llm_client
from app.models.schemas import Citation

logger = logging.getLogger("ai_journal.rag")

# ANSI color codes for prominent terminal demonstration logging
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RESET = "\033[0m"
BOLD = "\033[1m"


class RAGService:
    """
    Orchestrates the complete Retrieval-Augmented Generation (RAG) pipeline:
    1. Chunking & Ingestion with Supabase pgvector
    2. Multi-Tenant Semantic Retrieval strictly scoped to user_id
    3. Context-Rich Prompt Formulation with Citations
    4. Model-Agnostic LLM Generation (OpenRouter / Ollama)
    """

    def chunk_text(self, text: str, max_chunk_size: int = 400, overlap: int = 50) -> List[str]:
        """
        Splits journal entries into semantic chunks respecting sentence boundaries.
        Preserves high-signal context without blending disparate daily topics.
        """
        text = text.strip()
        if len(text) <= max_chunk_size:
            return [text]

        sentences = re.split(r'(?<=[.!?\n]) +', text)
        chunks: List[str] = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk = f"{current_chunk} {sentence}".strip() if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # Keep sliding window overlap
                if len(sentence) > max_chunk_size:
                    # Very long sentence: split mechanically
                    for i in range(0, len(sentence), max_chunk_size - overlap):
                        chunks.append(sentence[i:i + max_chunk_size])
                    current_chunk = ""
                else:
                    current_chunk = sentence

        if current_chunk and current_chunk not in chunks:
            chunks.append(current_chunk)

        return chunks

    async def ingest_note(self, entry_id: str, user_id: str, content: str, entry_date: date) -> int:
        """
        Ingests a journal note into the Supabase hosted vector database:
        - Chunks content
        - Generates dense vector embeddings
        - Upserts into 'journal_chunks' tagged with user_id and metadata
        """
        chunks = self.chunk_text(content)
        print(f"\n{BOLD}{CYAN}--- [RAG INGESTION] ---{RESET}")
        print(f"{CYAN}User ID:{RESET} {user_id}")
        print(f"{CYAN}Note ID:{RESET} {entry_id} (Date: {entry_date})")
        print(f"{CYAN}Generated Chunks:{RESET} {len(chunks)}")

        # Batch embed all chunks
        embeddings = embedding_service.embed_batch(chunks)

        supabase = get_supabase_client()
        chunk_records = []
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_records.append({
                "entry_id": entry_id,
                "user_id": user_id,
                "chunk_text": chunk_text,
                "chunk_index": idx,
                "entry_date": entry_date.isoformat(),
                "embedding": embedding
            })

        # Insert chunks into Supabase pgvector
        response = supabase.table("journal_chunks").insert(chunk_records).execute()
        print(f"{GREEN}✓ Successfully stored {len(chunk_records)} vector chunks in Supabase pgvector.{RESET}\n")
        return len(chunk_records)

    async def delete_note_vectors(self, entry_id: str, user_id: str) -> None:
        """
        Synchronizes note deletion with the vector database.
        Ensures deleted entries can no longer be retrieved by semantic search.
        """
        print(f"\n{BOLD}{YELLOW}--- [RAG VECTOR CLEANUP] ---{RESET}")
        print(f"{YELLOW}Purging vectors for Entry ID: {entry_id} (User: {user_id}){RESET}")
        supabase = get_supabase_client()
        supabase.table("journal_chunks").delete().match({"entry_id": entry_id, "user_id": user_id}).execute()
        print(f"{GREEN}✓ Vector synchronization complete.{RESET}\n")

    async def retrieve_relevant_context(
        self, query: str, user_id: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Executes semantic search against Supabase pgvector.
        CRITICAL FOR MULTI-TENANCY: strictly filters by filter_user_id.
        """
        query_vector = embedding_service.embed_text(query)

        print(f"\n{BOLD}{MAGENTA}================== [RAG RETRIEVAL PIPELINE] =================={RESET}")
        print(f"{BOLD}User Query:{RESET} \"{query}\"")
        print(f"{BOLD}Tenant Scoping (user_id):{RESET} {user_id}")

        supabase = get_supabase_client()
        try:
            # Call pgvector RPC function strictly filtered by authenticated user_id
            rpc_response = supabase.rpc(
                "match_journal_chunks",
                {
                    "query_embedding": query_vector,
                    "match_count": top_k,
                    "filter_user_id": user_id
                }
            ).execute()
            results = rpc_response.data or []
        except Exception as e:
            logger.error(f"Error calling match_journal_chunks RPC: {e}")
            print(f"{YELLOW}Warning: Supabase RPC unavailable, fallback empty results ({e}){RESET}")
            results = []

        print(f"{GREEN}Found {len(results)} matching chunks for user.{RESET}")
        for idx, item in enumerate(results, 1):
            score = item.get("similarity", 0.0)
            date_str = item.get("entry_date", "Unknown Date")
            snippet = item.get("chunk_text", "")[:70].replace("\n", " ")
            print(f"  [{idx}] Score: {score:.3f} | Date: {date_str} | \"{snippet}...\"")
        print(f"{MAGENTA}============================================================{RESET}\n")

        return results

    def build_prompt_messages(
        self, query: str, context_chunks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, str]], List[Citation]]:
        """
        Constructs context-rich messages for the LLM with strict citation guidance.
        """
        citations: List[Citation] = []

        if not context_chunks:
            context_text = "No relevant past journal entries were found for this question."
        else:
            context_blocks = []
            for item in context_chunks:
                e_id = str(item.get("entry_id", ""))
                e_date = str(item.get("entry_date", "Unknown Date"))
                txt = item.get("chunk_text", "").strip()
                sim = float(item.get("similarity", 0.0))

                context_blocks.append(f"[Date: {e_date} | NoteID: {e_id}]\n{txt}")
                citations.append(Citation(
                    entry_id=e_id,
                    entry_date=e_date,
                    snippet=txt[:150],
                    similarity=round(sim, 3)
                ))
            context_text = "\n\n---\n\n".join(context_blocks)

        system_instruction = (
            "You are a helpful, empathetic, and accurate personal AI Journal Assistant.\n"
            "Your objective is to answer questions or recall details STRICTLY based on the user's past journal entries provided below.\n"
            "\nRules:\n"
            "1. Only use facts explicitly stated in the context. If the context does not contain the answer, say honestly: "
            "'Based on your past journal entries, I don't have any record of that.' Do not fabricate details.\n"
            "2. Whenever citing information, explicitly reference the specific date (e.g., 'On Tuesday, Oct 12, you noted...').\n"
            "3. Maintain a warm, personal, and concise tone.\n"
            "\nPast Journal Entries Context:\n"
            f"{context_text}"
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": query}
        ]
        return messages, citations

    async def answer_query(self, query: str, user_id: str, top_k: int = 5) -> Tuple[str, List[Citation], str, str]:
        """Executes full RAG query returning complete text answer and citations."""
        chunks = await self.retrieve_relevant_context(query, user_id, top_k)
        messages, citations = self.build_prompt_messages(query, chunks)
        
        llm = get_llm_client()
        answer = await llm.generate(messages)
        return answer, citations, llm.provider_name, llm.model_name

    async def answer_query_stream(
        self, query: str, user_id: str, top_k: int = 5
    ) -> AsyncGenerator[str, None]:
        """
        Executes streaming RAG query yielding Server-Sent Events (SSE).
        Emits citations first, then tokens as they stream from OpenRouter/Ollama.
        """
        import json
        chunks = await self.retrieve_relevant_context(query, user_id, top_k)
        messages, citations = self.build_prompt_messages(query, chunks)

        llm = get_llm_client()

        # First SSE message: citations & metadata
        meta_event = {
            "type": "metadata",
            "provider": llm.provider_name,
            "model": llm.model_name,
            "citations": [c.model_dump() for c in citations]
        }
        yield f"data: {json.dumps(meta_event)}\n\n"

        # Subsequent SSE messages: token stream
        async for token in llm.generate_stream(messages):
            token_event = {"type": "token", "content": token}
            yield f"data: {json.dumps(token_event)}\n\n"

        # Completion signal
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


rag_service = RAGService()
