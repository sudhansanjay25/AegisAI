from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from groq import AsyncGroq

from app.db import get_session
from app.routers.score import score_output_internal  # reuse, don't duplicate

router = APIRouter(tags=["middleware"])

class Message(BaseModel):
    role: str
    content: str

class MiddlewareRequest(BaseModel):
    llm_provider: Literal["groq"]  # single-provider scope for now, per plan
    llm_api_key: str
    messages: list[Message]

async def call_downstream_llm(provider: str, api_key: str, messages: list[Message]) -> str:
    client = AsyncGroq(api_key=api_key)  # caller's own key — never stored or reused
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": m.role, "content": m.content} for m in messages],
    )
    return response.choices[0].message.content

@router.post("/v1/middleware/complete")
async def middleware_complete(
    payload: MiddlewareRequest,
    session: AsyncSession = Depends(get_session),
):
    llm_response_text = await call_downstream_llm(
        payload.llm_provider, payload.llm_api_key, payload.messages
    )

    score_result = await score_output_internal(llm_response_text, session)

    if score_result["policy_action"] == "allow":
        return {"response": llm_response_text, "governance": score_result}
    else:
        return {
            "response": "[Response withheld by AegisAI governance policy]",
            "governance": score_result,
        }
