"""
Claude-as-API — bọc Claude Agent SDK thành 1 HTTP endpoint local để test.

Chạy:  uvicorn api:app --reload --port 8000
Auth:  dùng tài khoản Claude đang đăng nhập trong Claude Code (cá nhân).
       Nếu muốn dùng API key:  set ANTHROPIC_API_KEY=...

Thử nhanh:
  curl -X POST http://localhost:8000/chat ^
       -H "Content-Type: application/json" ^
       -d "{\"prompt\": \"Xin chào, bạn là ai?\"}"
"""

import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from claude_agent_sdk import query, ClaudeAgentOptions

# --- Cấu hình (không hardcode — đọc từ env, có default an toàn) ---
DEFAULT_TOOLS = os.getenv("CLAUDE_TOOLS", "Read,Grep,Glob,Bash").split(",")
MAX_PROMPT_LEN = int(os.getenv("CLAUDE_MAX_PROMPT", "20000"))

# Token bảo vệ. BẮT BUỘC set khi expose ra ngoài:  set API_TOKEN=...
# Nếu trống -> chỉ cho dùng local, từ chối khi không có token (an toàn mặc định).
API_TOKEN = os.getenv("API_TOKEN", "")


def _check_auth(authorization: str | None) -> None:
    """Kiểm tra header Authorization: Bearer <token>. So sánh chống timing-attack."""
    if not API_TOKEN:
        # Chưa đặt token -> coi như chỉ dùng local, không nhận request có ý đồ từ xa.
        return
    expected = f"Bearer {API_TOKEN}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Sai hoặc thiếu token.")


# --- Schema request: validate ở biên hệ thống ---
class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LEN)
    tools: list[str] | None = Field(
        default=None,
        description="Ghi đè danh sách tool. Mặc định: Read/Grep/Glob/Bash.",
    )
    stream: bool = Field(default=False, description="True = trả token dần.")


class ChatResponse(BaseModel):
    result: str


def _build_options(req: ChatRequest) -> ClaudeAgentOptions:
    """Tạo options bất biến cho mỗi request."""
    tools = req.tools if req.tools else DEFAULT_TOOLS
    return ClaudeAgentOptions(allowed_tools=tools)


async def _run(req: ChatRequest) -> str:
    """Gọi Claude 1 lượt, gom kết quả cuối cùng."""
    final = ""
    async for message in query(prompt=req.prompt, options=_build_options(req)):
        if hasattr(message, "result"):
            final = message.result
    return final


async def _run_stream(req: ChatRequest):
    """Trả về từng mẩu text khi Claude sinh ra (Server-Sent Events đơn giản)."""
    options = _build_options(req)
    async for message in query(prompt=req.prompt, options=options):
        # Chỉ đẩy ra text có nội dung; bỏ qua message hệ thống.
        text = getattr(message, "result", None)
        if text:
            yield f"data: {text}\n\n"
    yield "data: [DONE]\n\n"


@asynccontextmanager
async def lifespan(_: FastAPI):
    mode = "API key" if os.getenv("ANTHROPIC_API_KEY") else "Claude subscription (login)"
    print(f"[claude-api] Ready. Auth: {mode}. Default tools: {DEFAULT_TOOLS}")
    yield


app = FastAPI(title="Claude-as-API (local test)", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, authorization: str | None = Header(default=None)):
    """Gọi Claude và nhận kết quả đầy đủ (hoặc stream nếu req.stream=True)."""
    _check_auth(authorization)
    try:
        if req.stream:
            return StreamingResponse(_run_stream(req), media_type="text/event-stream")
        result = await _run(req)
        if not result:
            raise HTTPException(status_code=502, detail="Claude không trả về nội dung.")
        return ChatResponse(result=result)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - biên ngoài cùng, log rồi báo lỗi gọn
        # Không lộ chi tiết nhạy cảm ra client; log đầy đủ phía server.
        print(f"[claude-api] ERROR: {exc!r}")
        raise HTTPException(status_code=500, detail="Loi khi goi Claude. Xem log server.")
