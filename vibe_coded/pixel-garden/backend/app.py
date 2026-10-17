import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

from .content import ROOT, load_exhibits
from .dialogue import DialogueService, RemarkRequest, RemarkResponse

remark_logger = logging.getLogger("pixel_garden.remarks")
if not remark_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    remark_logger.addHandler(handler)
remark_logger.setLevel(logging.INFO)


def create_app(service=None):
    # Only the app-local .env is loaded; unrelated repository credentials stay untouched.
    load_dotenv(ROOT / ".env", override=False)
    client = None
    if service is None:
        key = os.getenv("OPENAI_API_KEY")
        client = AsyncOpenAI(api_key=key, timeout=8, max_retries=0) if key else None
        service = DialogueService(load_exhibits(), client=client, model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                                  maximum=max(0, int(os.getenv("REMARK_MAX_GENERATIONS", "60"))))

    @asynccontextmanager
    async def lifespan(app):
        yield
        if client:
            await client.close()

    app = FastAPI(title="Pixel Garden", lifespan=lifespan)
    app.state.dialogue = service

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "dialogue": "configured" if service.client else "fallback"}

    @app.post("/api/remark", response_model=RemarkResponse)
    async def remark(request: RemarkRequest):
        if request.exhibit_id is not None and request.exhibit_id not in service.exhibits:
            raise HTTPException(status_code=422, detail="Unknown exhibit ID")
        return await service.remark(request)

    if (ROOT / "dist").is_dir():
        app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="garden")
    return app


app = create_app()
