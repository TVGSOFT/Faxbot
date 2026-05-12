from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FaxRequest(BaseModel):
    to: str = Field(..., description="Destination number in E.164 or national format")


class FaxJobOut(BaseModel):
    id: str
    to: str
    status: str
    error: Optional[str] = None
    pages: Optional[int] = None
    backend: str = "sip"  # "sip" or "phaxio"
    provider_sid: Optional[str] = None  # Phaxio fax ID or other cloud provider ID
    schedule_at: Optional[datetime] = None  # UTC timestamp for scheduled send; null = immediate
    app_id: Optional[str] = None           # Value of X-App-Id request header
    fcm_token: Optional[str] = None        # Firebase Cloud Messaging device token
    language: Optional[str] = None         # BCP-47 language code for notifications
    created_at: datetime
    updated_at: datetime
