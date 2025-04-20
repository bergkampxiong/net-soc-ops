from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ConfigFileBase(BaseModel):
    name: str
    device_type: str
    description: Optional[str] = None
    tags: List[str] = []
    status: str = "draft"  # draft or published

class ConfigFileCreate(ConfigFileBase):
    content: str

class ConfigFileUpdate(ConfigFileBase):
    content: Optional[str] = None

class ConfigVersion(BaseModel):
    version: int
    content: str
    comment: str
    created_at: datetime
    created_by: str

class ConfigFile(ConfigFileBase):
    id: str
    content: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    versions: List[ConfigVersion] = []

    class Config:
        orm_mode = True 