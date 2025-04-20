from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel

class ApiConfigBase(BaseModel):
    name: str
    type: str
    endpoint: str
    auth_type: str
    timeout: int = 30
    headers: Dict[str, str] = {}

class ApiConfigCreate(ApiConfigBase):
    pass

class ApiConfigUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    endpoint: Optional[str] = None
    auth_type: Optional[str] = None
    timeout: Optional[int] = None
    headers: Optional[Dict[str, str]] = None

class ApiConfig(ApiConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 