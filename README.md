# Personalized AI Journal (RAG MVP)

> Built for the **Codeacious AI Engineering Intern Assignment**.  
> Demonstrates a production-minded, clean architecture combining modern web fundamentals (Authentication, Multi-tenancy, Relational CRUD) with AI engineering techniques (Vector Embeddings, Supabase pgvector, LLM API Provider Abstraction, Token Streaming, and Source Citations).

---

## 1. System Architecture & Flow

```
[Frontend: React + Vite + TypeScript]
                  │
                  ▼ REST API + JWT / SSE Streams
       [FastAPI Application Backend]
       ├── /api/auth    (Password Hashing & JWT Verification)
       ├── /api/notes   (CRUD + Vector Ingestion/Purge)
       └── /api/chat    (RAG Pipeline + Streaming Tokens + Citations)
                  │
       ┌──────────┼──────────────────────┐
       ▼          ▼                      ▼
 [PostgreSQL]  [Hosted pgvector]   [LLM Abstraction Layer]
 (Relational)  (Cosine HNSW ANN)         │
                                  ┌──────┴──────┐
                                  ▼             ▼
                             [OpenRouter]   [Ollama]
                              (Cloud LLMs) (Local LLMs)
```

---

## 2. Key Architectural Explanations

### A. The LLM Provider Abstraction Layer (Ollama vs. OpenRouter)
To ensure the system is model-agnostic and avoids vendor lock-in, the LLM integration is decoupled behind an abstract interface (`BaseLLMClient`). Because both **OpenRouter** (for routing to cloud models like Claude 3.5, GPT-4o, and Llama 3) and **Ollama** (for local privacy-first models) adhere to the standard OpenAI API specification (`/v1/chat/completions`), we implemented a unified `OpenAICompatibleLLMClient`.

A factory method (`get_llm_client()`) dynamically inspects the `LLM_PROVIDER` environment variable at runtime. It configures the appropriate `BASE_URL`, `API_KEY`, and `MODEL_NAME` without requiring any modification to downstream RAG orchestration or business logic. It provides both non-streaming (`generate()`) and token-by-token streaming (`generate_stream()`) capabilities.

### B. Multi-Tenancy & Rigid Data Isolation in the Vector Database
Data isolation is enforced in depth at both the API layer and the database layer:
1. **Cryptographic Identity Verification:** Every protected request passes through FastAPI's dependency injection (`Depends(get_current_user)`), which cryptographically verifies the incoming JWT token and extracts the authenticated `user_id`.
2. **Relational Scoping:** Every relational query on `journal_entries` strictly includes `WHERE user_id = :authenticated_user_id`.
3. **Vector Database Scoping:** All embeddings in Supabase pgvector (`journal_chunks`) are stored with their corresponding `user_id`. During semantic similarity search, retrieval is executed via a PostgreSQL stored procedure (`match_journal_chunks`) that enforces `WHERE jc.user_id = filter_user_id`. User A can never retrieve, view, or compute similarity against User B's journal chunks.
4. **Delete/Update Synchronization:** Foreign keys are configured with `ON DELETE CASCADE`. When an entry is deleted or edited, vectors in the vector table are synchronously deleted/re-indexed, preventing stale or leaked information.

### C. Chunking Strategy
Personal journal entries often recount multifaceted days (e.g., breakfast details, work meetings, and evening reflections). Storing an entire daily entry as a single monolithic embedding tends to dilute specific semantic signals. 

We implemented a sentence-boundary-aware recursive chunker with sliding overlap (chunk size: ~400 characters, overlap: ~50 characters). Each chunk retains metadata: `user_id`, `entry_id`, `entry_date`, and `chunk_index`. This ensures that specific queries (e.g., *"What did I eat on Tuesday?"*) match the precise sentence where food was mentioned with high cosine similarity, rather than being overshadowed by other topics from that day.

### D. Justification of Dependencies / Imports
* **`fastapi` & `uvicorn`:** Modern, high-throughput asynchronous web framework with native dependency injection and automatic OpenAPI validation.
* **`pydantic` & `pydantic-settings`:** Enforces strict runtime data validation and clean environment variable management.
* **`supabase`:** Official Python client enabling direct communication with Supabase PostgreSQL and pgvector RPC functions.
* **`openai`:** Official Python SDK client used strictly to interface with both OpenRouter and Ollama via the unified OpenAI API specification.
* **`fastembed`:** Ultra-lightweight ONNX-runtime embedding library that runs locally on CPU with zero GPU requirement, 3x faster than PyTorch, and with zero external API fees.
* **`python-jose` & `passlib[bcrypt]`:** Battle-tested password hashing and JWT token claims signing.

---

## 3. Step-by-Step Local Setup Instructions

### Prerequisites
* Python 3.10+
* Node.js 18+ & npm
* A free [Supabase](https://supabase.com) account (or existing PostgreSQL instance with pgvector)
* An [OpenRouter](https://openrouter.ai/) API key (or [Ollama](https://ollama.ai/) running locally)

---

### Step 1: Database Setup in Supabase
1. Create a new project in your Supabase dashboard.
2. Navigate to the **SQL Editor** tab on the left sidebar.
3. Open the file [`backend/supabase_schema.sql`](./backend/supabase_schema.sql), paste its entire contents into the Supabase SQL Editor, and click **Run**.
   * *This creates the `vector` extension, `users`, `journal_entries`, `journal_chunks` tables, HNSW indexes, and the `match_journal_chunks` multi-tenant function.*
4. In Supabase, navigate to **Project Settings -> API** and copy:
   * **Project URL**
   * **`service_role` Secret Key** (needed to manage and query vector tables).

---

### Step 2: Backend Configuration & Startup
1. Open a terminal in the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your `.env` file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and configure:
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-supabase-service-role-key

   # --- Toggle: OpenRouter vs Ollama ---
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here
   OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
   ```
   *(To use Ollama locally instead, simply set `LLM_PROVIDER=ollama`)*

5. Run unit tests to verify:
   ```bash
   pytest
   ```
6. Start the FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   *FastAPI docs will be available at: http://localhost:8000/docs*

---

### Step 3: Frontend Setup & Startup
1. Open a new terminal in the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open your browser at: **`http://localhost:3000`**

---

## 4. Testing the Stretch Goals

1. **Token-by-Token Streaming:** Ask a question in the chat interface. Notice tokens streaming into the message bubble in real-time via Server-Sent Events (SSE).
2. **Source Citations:** Notice the green badge under assistant responses showing the exact entry date and cosine similarity score.
3. **Delete/Update Synchronization:** Click the trash icon on a note. Verify that the note is deleted and its vectors are purged from the vector database.
4. **Multi-Tenancy Verification:**
   - Log in as `alice@example.com` and add a private note: *"My secret code is 8842."*
   - Log out and register `bob@example.com`.
   - Ask: *"What is my secret code?"*
   - Bob will receive: *"Based on your past journal entries, I don't have any record of that."*

---

## 5. Terminal Logs for Video Demo

When recording your 1-3 minute screen demo, keep your backend terminal visible! The application prints structured logs during ingestion and retrieval:

```text
================== [RAG RETRIEVAL PIPELINE] ==================
User Query: "What did I eat on Tuesday?"
Tenant Scoping (user_id): 3f1e9480-1a2b-4c3d-8e4f-56789abcdef0
Found 1 matching chunks for user.
  [1] Score: 0.884 | Date: 2026-09-20 | "On Tuesday morning I had oatmeal with blueberries and honey..."
============================================================
```
