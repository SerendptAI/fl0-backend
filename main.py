from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.routers import submissions, search, auth
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup logic if needed
    yield
    # shutdown logic if needed

app = FastAPI(
    title="Semantic Search Autofill API",
    description="A smart backend for form autofill using Vector Search.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(submissions.router, prefix="/api/v1/submissions")
app.include_router(search.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1/auth")

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "app" / "static"), name="static")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
