from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

class SubmissionCreate(BaseModel):
    website: str
    data: Dict[str, Any]

class SubmissionResponse(BaseModel):
    id: str
    user_id: str
    website: str
    data: Dict[str, Any]
    timestamp: datetime

class SubmissionSummary(BaseModel):
    id: str
    user_id: str
    website: str
    timestamp: datetime

class AutofillRequest(BaseModel):
    keys: List[str]
    threshold: float = Field(0.8, ge=0.0, le=1.0, description="Minimum similarity score")
    multiple: bool = Field(False, description="Return multiple suggestions if true")
    limit: int = Field(3, ge=1, description="Max suggestions per key if multiple is true")

class AutofillResponse(BaseModel):
    suggestions: Dict[str, Union[str, List[str], None]]
