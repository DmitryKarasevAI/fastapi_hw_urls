from pydantic import BaseModel
from typing import Optional


class URLCreate(BaseModel):
    full_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[str] = None
