from sqlalchemy import Column, String, DateTime
from database.base import Base
import datetime

class ApiConfig(Base):
    __tablename__ = "api_configs"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    method = Column(String, nullable=False)
    headers = Column(String)
    body = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    updated_by = Column(String, nullable=False) 