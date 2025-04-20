from typing import List, Optional
import jinja2
import textfsm
from datetime import datetime
import uuid
from schemas.config import ConfigFileCreate, ConfigFileUpdate, ConfigFile, ConfigVersion
from database.session import get_db
from sqlalchemy import and_, or_, desc
from database.config_models import ConfigFile as ConfigFileModel, ConfigVersion as ConfigVersionModel

class ConfigManagementService:
    def __init__(self):
        self.db = next(get_db())
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("templates/"),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def create_config(self, config: ConfigFileCreate, user_id: str) -> ConfigFile:
        config_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        config_dict = config.dict()
        config_dict.update({
            "id": config_id,
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "updated_by": user_id
        })
        
        db_config = ConfigFileModel(**config_dict)
        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)
        return ConfigFile.from_orm(db_config)
    
    def get_configs(
        self,
        skip: int = 0,
        limit: int = 10,
        name: Optional[str] = None,
        device_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ConfigFile]:
        query = self.db.query(ConfigFileModel)
        
        # 应用过滤条件
        if name:
            query = query.filter(ConfigFileModel.name.ilike(f"%{name}%"))
        if device_type:
            query = query.filter(ConfigFileModel.device_type == device_type)
        if tags:
            # 对于JSON数组字段的查询
            for tag in tags:
                query = query.filter(ConfigFileModel.tags.contains([tag]))
        if status:
            query = query.filter(ConfigFileModel.status == status)
        if start_date:
            query = query.filter(ConfigFileModel.created_at >= start_date.isoformat())
        if end_date:
            query = query.filter(ConfigFileModel.created_at <= end_date.isoformat())
        
        configs = query.offset(skip).limit(limit).all()
        return [ConfigFile.from_orm(config) for config in configs]
    
    def get_config(self, config_id: str) -> Optional[ConfigFile]:
        db_config = self.db.query(ConfigFileModel).filter(ConfigFileModel.id == config_id).first()
        if db_config is None:
            return None
        config = ConfigFile.from_orm(db_config)
        # 获取版本信息
        config.versions = self.get_versions(config_id)
        return config
    
    def update_config(self, config_id: str, config: ConfigFileUpdate, user_id: str) -> Optional[ConfigFile]:
        db_config = self.db.query(ConfigFileModel).filter(ConfigFileModel.id == config_id).first()
        if not db_config:
            return None
        
        update_data = config.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.now().isoformat()
        update_data["updated_by"] = user_id
        
        for key, value in update_data.items():
            setattr(db_config, key, value)
        
        self.db.commit()
        self.db.refresh(db_config)
        return ConfigFile.from_orm(db_config)
    
    def delete_config(self, config_id: str) -> bool:
        db_config = self.db.query(ConfigFileModel).filter(ConfigFileModel.id == config_id).first()
        if not db_config:
            return False
        
        self.db.delete(db_config)
        self.db.commit()
        return True
    
    def create_version(self, config_id: str, content: str, comment: str, user_id: str) -> ConfigVersion:
        """创建新的配置版本"""
        version = ConfigVersionModel(
            id=str(uuid.uuid4()),
            config_id=config_id,
            content=content,
            comment=comment,
            created_by=user_id,
            created_at=datetime.now().isoformat(),
            version=self._get_next_version(config_id)
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return ConfigVersion.from_orm(version)
    
    def get_versions(self, config_id: str, limit: int = 10) -> List[ConfigVersion]:
        """获取配置的版本历史"""
        versions = self.db.query(ConfigVersionModel).filter(
            ConfigVersionModel.config_id == config_id
        ).order_by(desc(ConfigVersionModel.version)).limit(limit).all()
        return [ConfigVersion.from_orm(version) for version in versions]
    
    def render_template(self, template_name: str, **kwargs) -> str:
        template = self.jinja_env.get_template(template_name)
        return template.render(**kwargs)
    
    def parse_with_textfsm(self, template_name: str, raw_text: str) -> List[dict]:
        with open(f"templates/textfsm/{template_name}") as f:
            template = textfsm.TextFSM(f)
            result = template.ParseText(raw_text)
            return [dict(zip(template.header, row)) for row in result]
    
    def get_version(self, config_id: str, version_id: str) -> Optional[ConfigVersion]:
        """获取特定版本的配置"""
        return self.db.query(ConfigVersionModel).filter(
            ConfigVersionModel.config_id == config_id,
            ConfigVersionModel.id == version_id
        ).first()
    
    def rollback_to_version(self, config_id: str, version_id: str, user_id: str) -> bool:
        """回滚到指定版本"""
        version = self.get_version(config_id, version_id)
        if not version:
            return False
            
        config = self.get_config(config_id)
        if not config:
            return False
            
        # 创建新版本作为回滚记录
        new_version = self.create_version(config_id, version.content, version.comment, user_id)
        
        # 更新当前配置内容
        config.content = version.content
        config.updated_at = datetime.utcnow()
        config.updated_by = user_id
        
        self.db.commit()
        return True
    
    def _get_next_version(self, config_id: str) -> int:
        """获取下一个版本号"""
        latest = self.db.query(ConfigVersionModel).filter(
            ConfigVersionModel.config_id == config_id
        ).order_by(desc(ConfigVersionModel.version)).first()
        
        return (latest.version + 1) if latest else 1 