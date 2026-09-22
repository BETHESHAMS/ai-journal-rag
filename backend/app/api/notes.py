import logging
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from app.core.database import get_supabase_client
from app.models.schemas import JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse, UserResponse
from app.api.deps import get_current_user
from app.services.rag_service import rag_service

logger = logging.getLogger("ai_journal.notes")
router = APIRouter(prefix="/notes", tags=["Journal Entries"])


@router.post("", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_in: JournalEntryCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Creates a new journal entry and triggers vector ingestion:
    1. Saves note in PostgreSQL table 'journal_entries' strictly tagged with current_user.id
    2. Chunks text and computes dense embeddings
    3. Upserts vector chunks into 'journal_chunks' tagged with current_user.id
    """
    supabase = get_supabase_client()
    entry_date = note_in.entry_date

    # 1. Insert relational record
    insert_res = supabase.table("journal_entries").insert({
        "user_id": current_user.id,
        "content": note_in.content,
        "entry_date": entry_date.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).execute()

    if not insert_res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist journal entry."
        )

    saved_note = insert_res.data[0]
    note_id = str(saved_note["id"])

    # 2. Ingest into vector store
    try:
        await rag_service.ingest_note(
            entry_id=note_id,
            user_id=current_user.id,
            content=note_in.content,
            entry_date=entry_date
        )
    except Exception as e:
        logger.error(f"Vector ingestion failed for note {note_id}: {e}")
        # Note is still saved in relational DB; log warning

    return JournalEntryResponse(**saved_note)


@router.get("", response_model=List[JournalEntryResponse])
async def list_notes(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Retrieves all journal entries belonging strictly to the authenticated user.
    MULTI-TENANCY GUARANTEE: Filtered rigidly by current_user.id.
    """
    supabase = get_supabase_client()
    query_res = supabase.table("journal_entries")\
        .select("*")\
        .eq("user_id", current_user.id)\
        .order("entry_date", desc=True)\
        .order("created_at", desc=True)\
        .execute()

    return [JournalEntryResponse(**item) for item in (query_res.data or [])]


@router.get("/{note_id}", response_model=JournalEntryResponse)
async def get_note(
    note_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Retrieves a single note ensuring strict tenant ownership."""
    supabase = get_supabase_client()
    query_res = supabase.table("journal_entries")\
        .select("*")\
        .eq("id", note_id)\
        .eq("user_id", current_user.id)\
        .execute()

    if not query_res.data or len(query_res.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found or access denied."
        )

    return JournalEntryResponse(**query_res.data[0])


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    STRETCH GOAL: Delete/Update Sync.
    Deletes the journal entry and synchronously purges all corresponding vector embeddings
    from Supabase pgvector so the note is immediately removed from future RAG context.
    """
    supabase = get_supabase_client()

    # Verify ownership before deletion
    existing = supabase.table("journal_entries")\
        .select("id")\
        .eq("id", note_id)\
        .eq("user_id", current_user.id)\
        .execute()

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found or access denied."
        )

    # 1. Purge vectors from vector database
    await rag_service.delete_note_vectors(entry_id=note_id, user_id=current_user.id)

    # 2. Delete relational entry (also triggers ON DELETE CASCADE in PostgreSQL)
    supabase.table("journal_entries").delete().eq("id", note_id).eq("user_id", current_user.id).execute()

    return None


@router.put("/{note_id}", response_model=JournalEntryResponse)
async def update_note(
    note_id: str,
    note_in: JournalEntryUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    STRETCH GOAL: Delete/Update Sync.
    Updates journal note content and re-syncs embeddings in pgvector.
    """
    supabase = get_supabase_client()

    # Verify ownership
    existing = supabase.table("journal_entries")\
        .select("*")\
        .eq("id", note_id)\
        .eq("user_id", current_user.id)\
        .execute()

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found or access denied."
        )

    current_data = existing.data[0]
    updated_content = note_in.content if note_in.content is not None else current_data["content"]
    updated_date = note_in.entry_date.isoformat() if note_in.entry_date else current_data["entry_date"]

    # 1. Update relational record
    update_res = supabase.table("journal_entries").update({
        "content": updated_content,
        "entry_date": updated_date,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", note_id).eq("user_id", current_user.id).execute()

    # 2. If content changed, purge old vectors and re-embed new content
    if note_in.content is not None:
        await rag_service.delete_note_vectors(entry_id=note_id, user_id=current_user.id)
        from datetime import date
        d = note_in.entry_date or date.fromisoformat(str(current_data["entry_date"]))
        await rag_service.ingest_note(
            entry_id=note_id,
            user_id=current_user.id,
            content=updated_content,
            entry_date=d
        )

    return JournalEntryResponse(**update_res.data[0])
