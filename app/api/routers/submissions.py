from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from typing import List, Optional
from app.core.auth import get_current_user
from app.models.schemas import SubmissionCreate, SubmissionResponse, SubmissionSummary
from app.services import vector_service
from app.core.database import get_database
from datetime import datetime
from uuid import uuid4

router = APIRouter(tags=["Submissions"])

@router.post("/", response_model=SubmissionResponse)
async def ingest_submission(
    submission: SubmissionCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Ingest a new form submission.
    - Upserts by (user_id, website, path, form_id).
    - Merges data: new keys are added, existing keys accumulate unique values as arrays.
    - Triggers asynchronous vector embedding.
    """
    user_id = current_user["user_id"]

    # composite key for uniqueness
    filter_doc = {
        "user_id": user_id,
        "website": submission.website,
        "path": submission.path,
        "form_id": submission.form_id,
    }

    # $addToSet appends only unique values, auto-creates array on first insert
    add_to_set_ops = {}
    for key, value in submission.data.items():
        add_to_set_ops[f"data.{key}"] = str(value)

    update_doc = {
        "$addToSet": add_to_set_ops,
        "$setOnInsert": {
            "id": str(uuid4()),
            "user_id": user_id,
            "website": submission.website,
            "path": submission.path,
            "form_id": submission.form_id,
        },
        "$set": {"timestamp": datetime.utcnow()},
    }

    await db.submissions.update_one(filter_doc, update_doc, upsert=True)

    # fetch the final merged document to return
    submission_doc = await db.submissions.find_one(filter_doc)

    # background vector ingestion (uses original submission data, not merged)
    background_tasks.add_task(vector_service.ingest_submission, user_id, submission)

    return submission_doc

@router.get("/", response_model=List[SubmissionSummary])
async def list_submissions(
    website: Optional[str] = Query(None, description="Filter by website URL"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get a list of submissions.
    """
    user_id = current_user["user_id"]
    query = {"user_id": user_id}
    if website:
        query["website"] = website

    cursor = db.submissions.find(query, {"data": 0})
    submissions = await cursor.to_list(length=100)
    return submissions

@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission_detail(
    submission_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get the full data for a specific submission by ID.
    """
    user_id = current_user["user_id"]
    submission = await db.submissions.find_one({"id": submission_id, "user_id": user_id})

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return submission

