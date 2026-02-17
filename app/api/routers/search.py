from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.models.schemas import AutofillRequest, AutofillResponse
from app.services import vector_service

router = APIRouter(tags=["Search"])

@router.post("/autofill", response_model=AutofillResponse)
async def autofill_form(
    request: AutofillRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Smart Autofill.
    - Takes a list of keys (field names).
    - Searches vector store for semantic matches in user's history.
    - Returns suggested values.
    """
    user_id = current_user["user_id"]
    results = await vector_service.search_autofill(user_id, request)
    print(f"[autofill] results: {results}")
    return {"suggestions": results}
