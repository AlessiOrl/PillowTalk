from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.config import get_settings
from app.database import get_session
from app.models.group import Group
from app.models.prompt_session import PromptSession
from app.models.question import Question
from app.models.user import User
from app.services.group_service import GroupService
from app.services.question_service import QuestionService

router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBearer(auto_error=False)
settings = get_settings()


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


async def require_admin_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> None:
    if credentials is None or credentials.credentials != settings.admin_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


@router.get("/stats", dependencies=[Depends(require_admin_token)])
async def admin_stats() -> dict[str, Any]:
    async with get_session() as session:
        question_service = QuestionService(session)
        current_prompt = await question_service.get_current_prompt()
        user_count = int((await session.scalar(select(func.count(User.id)))) or 0)
        question_count = int((await session.scalar(select(func.count(Question.id)))) or 0)
        group_count = int((await session.scalar(select(func.count(Group.id)))) or 0)
        prompt_count = int((await session.scalar(select(func.count(PromptSession.id)))) or 0)

    return {
        "users": user_count,
        "questions": question_count,
        "groups": group_count,
        "prompt_sessions": prompt_count,
        "current_prompt": {
            "id": current_prompt.id,
            "asked_on": current_prompt.asked_on.isoformat(),
            "question": current_prompt.question.text,
        }
        if current_prompt is not None
        else None,
    }


@router.post("/reload-questions", dependencies=[Depends(require_admin_token)])
async def reload_questions(request: Request) -> dict[str, Any]:
    count = await request.app.state.reimport_questions()
    return {"imported": count}


@router.post("/force-question", dependencies=[Depends(require_admin_token)])
async def force_question(request: Request) -> dict[str, Any]:
    dispatch = await request.app.state.bot_service.dispatch_next_prompt(force_new=True, source="api")
    return {
        "prompt_session_id": dispatch.prompt_session.id,
        "question_id": dispatch.prompt_session.question_id,
        "question": dispatch.prompt_session.question.text,
        "created": dispatch.created,
    }


@router.get("/groups", dependencies=[Depends(require_admin_token)])
async def list_groups() -> list[dict[str, Any]]:
    async with get_session() as session:
        groups = await GroupService(session).list_groups()

    return [
        {
            "id": group.id,
            "name": group.name,
            "invite_code": group.invite_code,
            "member_count": member_count,
        }
        for group, member_count in groups
    ]


@router.post("/groups", dependencies=[Depends(require_admin_token)])
async def create_group(payload: GroupCreateRequest) -> dict[str, Any]:
    async with get_session() as session:
        group = await GroupService(session).create_group(payload.name, settings.admin_telegram_id)

    return {"id": group.id, "name": group.name, "invite_code": group.invite_code}


@router.get("/question-history", dependencies=[Depends(require_admin_token)])
async def question_history() -> dict[str, Any]:
    async with get_session() as session:
        question_service = QuestionService(session)
        total = await question_service.count_questions()
        remaining = await question_service.count_remaining_questions()
        prompts = await question_service.list_asked_questions()

    history = []
    for prompt in prompts:
        answered_by = [
            {
                "user_id": answer.user_id,
                "display_name": answer.user.display_name if answer.user else None,
                "nickname": answer.user.nickname if answer.user else None,
                "answered_at": answer.created_at.isoformat(),
            }
            for answer in prompt.answers
        ]
        history.append({
            "prompt_session_id": prompt.id,
            "question_id": prompt.question_id,
            "question": prompt.question.text,
            "asked_on": prompt.asked_on.isoformat(),
            "source": prompt.source,
            "answered_by": answered_by,
        })

    return {
        "total_questions": total,
        "remaining_unasked": remaining,
        "asked": history,
    }
