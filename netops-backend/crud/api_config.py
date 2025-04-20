from sqlalchemy.orm import Session
from typing import List, Optional
from database.category_models import ApiConfig
from schemas.api_config import ApiConfigCreate, ApiConfigUpdate

def get_api_config(db: Session, api_config_id: int) -> Optional[ApiConfig]:
    return db.query(ApiConfig).filter(ApiConfig.id == api_config_id).first()

def get_api_configs(db: Session, skip: int = 0, limit: int = 100) -> List[ApiConfig]:
    return db.query(ApiConfig).offset(skip).limit(limit).all()

def create_api_config(db: Session, api_config: ApiConfigCreate) -> ApiConfig:
    db_api_config = ApiConfig(**api_config.model_dump())
    db.add(db_api_config)
    db.commit()
    db.refresh(db_api_config)
    return db_api_config

def update_api_config(db: Session, api_config_id: int, api_config: ApiConfigUpdate) -> Optional[ApiConfig]:
    db_api_config = get_api_config(db, api_config_id)
    if not db_api_config:
        return None
    
    update_data = api_config.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_api_config, field, value)
    
    db.commit()
    db.refresh(db_api_config)
    return db_api_config

def delete_api_config(db: Session, api_config_id: int) -> bool:
    db_api_config = get_api_config(db, api_config_id)
    if not db_api_config:
        return False
    
    db.delete(db_api_config)
    db.commit()
    return True 