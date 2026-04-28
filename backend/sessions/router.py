import logging
from fastapi import APIRouter, HTTPException, Depends
from .models import (
    SessionSummary, SessionDetail, MessageResponse,
    CreateSessionRequest, UpdateTitleRequest,
)
from ..auth.utils import get_current_user, TokenData
from ..database import supabase

logger = logging.getLogger("sessions")
router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


@router.get("/", response_model=list[SessionSummary])
async def list_sessions(current_user: TokenData = Depends(get_current_user)):
    try:
        sessions_result = (
            supabase.table("sessions")
            .select("id,title,created_at,updated_at")
            .eq("user_id", current_user.user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        summaries = []
        for s in sessions_result.data:
            last_msg = (
                supabase.table("messages")
                .select("content")
                .eq("session_id", s["id"])
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            preview = last_msg.data[0]["content"][:100] if last_msg.data else None
            summaries.append(SessionSummary(
                id=s["id"],
                title=s["title"],
                created_at=str(s["created_at"]),
                updated_at=str(s["updated_at"]),
                last_message_preview=preview,
            ))
        return summaries
    except Exception:
        logger.exception("List sessions failed")
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.post("/", response_model=SessionSummary)
async def create_session(
    req: CreateSessionRequest,
    current_user: TokenData = Depends(get_current_user),
):
    try:
        result = supabase.table("sessions").insert({
            "user_id": current_user.user_id,
            "title": req.title or "New Chat",
        }).execute()
        s = result.data[0]
        return SessionSummary(
            id=s["id"],
            title=s["title"],
            created_at=str(s["created_at"]),
            updated_at=str(s["updated_at"]),
        )
    except Exception:
        logger.exception("Create session failed")
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    try:
        session_result = (
            supabase.table("sessions")
            .select("id,title,user_id,created_at")
            .eq("id", session_id)
            .execute()
        )
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Session not found")
        session = session_result.data[0]
        if session["user_id"] != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your session")

        msgs_result = (
            supabase.table("messages")
            .select("id,role,content,canvas_data,created_at")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        messages = [
            MessageResponse(
                id=m["id"],
                role=m["role"],
                content=m["content"],
                canvas_data=m.get("canvas_data"),
                created_at=str(m["created_at"]),
            )
            for m in msgs_result.data
        ]
        return SessionDetail(
            id=session["id"],
            title=session["title"],
            messages=messages,
            created_at=str(session["created_at"]),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Get session failed")
        raise HTTPException(status_code=500, detail="Failed to fetch session")


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    try:
        session_result = (
            supabase.table("sessions")
            .select("user_id")
            .eq("id", session_id)
            .execute()
        )
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Session not found")
        if session_result.data[0]["user_id"] != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your session")
        supabase.table("sessions").delete().eq("id", session_id).execute()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Delete session failed")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.put("/{session_id}")
async def update_session_title(
    session_id: str,
    req: UpdateTitleRequest,
    current_user: TokenData = Depends(get_current_user),
):
    try:
        session_result = (
            supabase.table("sessions")
            .select("user_id")
            .eq("id", session_id)
            .execute()
        )
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Session not found")
        if session_result.data[0]["user_id"] != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your session")

        result = (
            supabase.table("sessions")
            .update({"title": req.title})
            .eq("id", session_id)
            .execute()
        )
        s = result.data[0]
        return {"id": s["id"], "title": s["title"]}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Update session title failed")
        raise HTTPException(status_code=500, detail="Failed to update session")
