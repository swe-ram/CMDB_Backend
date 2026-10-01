import os

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

app = FastAPI(
    title="Slack License Inventory API",
    version="1.0.0",
    description="Centralized Slack license inventory and usage collection for enterprise license management.",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
)
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "Slack License Inventory API",
    }


from routers.slack import router as slack_router

app.include_router(slack_router)