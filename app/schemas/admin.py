# app/schemas/admin.py
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


class AdminStatsResponse(BaseModel):
    total_members: int
    new_members_this_month: int
    pending_suggestions: int
    books_in_queue: int
    tracking_progress: int        # members tracking current book
    avg_chapter: float            # average chapter across trackers


class AdminLogResponse(BaseModel):
    """
    Flat log entry for the admin activity table.
    target_data is the parsed JSON from the Text column.
    """
    id: int
    admin_id: Optional[int]
    admin_name: Optional[str]
    action: str
    target_data: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminLogDetailResponse(BaseModel):
    """Paginated wrapper for the admin log list."""
    logs: list[AdminLogResponse]
    total: int
    page: int
    page_size: int