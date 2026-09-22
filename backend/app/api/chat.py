import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatQueryRequest, ChatQueryResponse, UserResponse
from app.api.deps import get_current_user
from app.services.rag_service import rag_service

logger = logging.getLogger("ai_journal.chat")
router = APIRouter(prefix="/chat", tags=["RAG AI Assistant"])


@router.post("", response_model=ChatQueryResponse)
async def query_journal_rag(
    req: ChatQueryRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Standard (non-streaming) RAG query endpoint.
    Retrieves user's top-k semantic matches and prompts the configured LLM.
    Returns the answer together with source citations and provider metadata.
    """
    try:
        answer, citations, provider, model = await rag_service.answer_query(
            query=req.query,
            user_id=current_user.id,
            top_k=req.top_k
        )
        return ChatQueryResponse(
            answer=answer,
            citations=citations,
            provider_used=provider,
            model_used=model
        )
    except Exception as e:
        logger.error(f"Error executing RAG query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Assistant failed to generate response: {str(e)}"
        )


@router.post("/stream")
async def query_journal_rag_stream(
    req: ChatQueryRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    STRETCH GOAL: Streaming Responses.
    Streams token-by-token LLM completions via Server-Sent Events (SSE).
    Emits metadata (citations, provider, model) as the first event, followed by tokens.
    """
    return StreamingResponse(
        rag_service.answer_query_stream(
            query=req.query,
            user_id=current_user.id,
            top_k=req.top_k
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
