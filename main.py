import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.routers import submissions, search, auth
from app.core.database import db
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # migrate: backfill path and form_id (handles both missing and null)
    await db.submissions.update_many(
        {"path": {"$in": [None]}},
        {"$set": {"path": "/"}}
    )
    await db.submissions.update_many(
        {"path": {"$exists": False}},
        {"$set": {"path": "/"}}
    )
    await db.submissions.update_many(
        {"form_id": {"$exists": False}},
        {"$set": {"form_id": None}}
    )

    # migrate: convert all string data values to single-element arrays
    async for doc in db.submissions.find({"data": {"$exists": True}}):
        updates = {}
        if doc.get("data"):
            for key, value in doc["data"].items():
                if not isinstance(value, list):
                    updates[f"data.{key}"] = [str(value)]
        if updates:
            await db.submissions.update_one(
                {"_id": doc["_id"]},
                {"$set": updates}
            )

    # migrate: deduplicate docs that share the same composite key
    pipeline = [
        {"$group": {
            "_id": {"user_id": "$user_id", "website": "$website", "path": "$path", "form_id": "$form_id"},
            "docs": {"$push": {"_id": "$_id", "data": "$data"}},
            "count": {"$sum": 1}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    async for group in db.submissions.aggregate(pipeline):
        docs = group["docs"]
        keep = docs[0]
        for dup in docs[1:]:
            if dup.get("data"):
                for key, value in dup["data"].items():
                    vals = value if isinstance(value, list) else [str(value)]
                    await db.submissions.update_one(
                        {"_id": keep["_id"]},
                        {"$addToSet": {f"data.{key}": {"$each": vals}}}
                    )
            await db.submissions.delete_one({"_id": dup["_id"]})
        logger.info(f"Merged {len(docs) - 1} duplicate(s) for {group['_id']}")

    # now safe to create the unique index
    await db.submissions.create_index(
        [("user_id", 1), ("website", 1), ("path", 1), ("form_id", 1)],
        unique=True,
        name="unique_form_submission",
    )
    yield

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

