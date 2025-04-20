from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ConfigFileBase(BaseModel):
    name: str
    template_type: str
    content: str
    description: Optional[str] = None
    status: str = "draft"
    device_type: str = "default"
    tags: List[str] = []

class ConfigFileCreate(ConfigFileBase):
    pass

class ConfigFileUpdate(ConfigFileBase):
    pass

class ConfigFile(ConfigFileBase):
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 