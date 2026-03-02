from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

class SubmissionCreate(BaseModel):
    website: str
    path: str = Field("/", description="Page path within the website")
    form_id: Optional[str] = Field(None, description="Optional form identifier for multiple forms on one page")
    data: Dict[str, Any]

class SubmissionResponse(BaseModel):
    id: str
    user_id: str
    website: str
    path: str
    form_id: Optional[str] = None
    data: Dict[str, List[str]]
    latest: Dict[str, Optional[str]] = {}
    timestamp: datetime

class SubmissionSummary(BaseModel):
    id: str
    user_id: str
    website: str
    path: str
    form_id: Optional[str] = None
    timestamp: datetime

class AutofillRequest(BaseModel):
    keys: List[str]
    website: Optional[str] = Field(None, description="Filter suggestions by website")
    path: Optional[str] = Field(None, description="Filter suggestions by path")
    form_id: Optional[str] = Field(None, description="Filter suggestions by form id")
    threshold: float = Field(0.8, ge=0.0, le=1.0, description="Minimum similarity score")
    multiple: bool = Field(False, description="Return multiple suggestions if true")
    limit: int = Field(3, ge=1, description="Max websites to return and max suggestions per key if multiple is true")

class WebsiteSuggestion(BaseModel):
    website: str
    fields: Dict[str, Union[str, List[str], None]]

class AutofillResponse(BaseModel):
    suggestions: List[WebsiteSuggestion]

class RefreshTokenRequest(BaseModel):
    refresh_token: str
