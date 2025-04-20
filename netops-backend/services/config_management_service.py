from typing import List, Optional
from sqlalchemy.orm import Session
from database.config_management_models import ConfigFile as DBConfigFile
from schemas.config_management import ConfigFileCreate, ConfigFileUpdate, ConfigFile
from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.sql import select
from sqlalchemy.ext.asyncio import AsyncSession
import pytz

class ConfigManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.timezone = pytz.timezone('Asia/Shanghai')

    def get_configs(
        self,
        skip: int = 0,
        limit: int = 10,
        name: Optional[str] = None,
        device_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        template_type: Optional[str] = None
    ) -> List[ConfigFile]:
        try:
            # 构建基础查询
            query = self.db.query(DBConfigFile)
            
            # 应用过滤条件
            if name:
                query = query.filter(DBConfigFile.name.ilike(f"%{name}%"))
            if device_type:
                query = query.filter(DBConfigFile.device_type == device_type)
            if status:
                query = query.filter(DBConfigFile.status == status)
            if start_date:
                # 将输入的时间转换为UTC时间
                start_date_utc = self.timezone.localize(start_date).astimezone(pytz.UTC)
                query = query.filter(DBConfigFile.created_at >= start_date_utc)
            if end_date:
                # 将输入的时间转换为UTC时间
                end_date_utc = self.timezone.localize(end_date).astimezone(pytz.UTC)
                query = query.filter(DBConfigFile.created_at <= end_date_utc)
            if template_type:
                query = query.filter(DBConfigFile.template_type == template_type)
            
            # 执行查询
            configs = query.offset(skip).limit(limit).all()
            
            # 手动过滤template_type
            if template_type:
                configs = [config for config in configs if config.template_type == template_type]
            
            # 转换为响应模型
            result = [self._convert_to_response_model(config) for config in configs]
            return result
        except Exception as e:
            raise Exception(f"获取配置列表失败: {str(e)}")

    def get_config(self, config_id: int) -> Optional[ConfigFile]:
        try:
            db_config = self.db.query(DBConfigFile).filter(DBConfigFile.id == config_id).first()
            if db_config:
                return self._convert_to_response_model(db_config)
            return None
        except Exception as e:
            raise Exception(f"获取配置失败: {str(e)}")

    def _get_db_config(self, config_id: int) -> Optional[DBConfigFile]:
        """获取数据库模型"""
        try:
            return self.db.query(DBConfigFile).filter(DBConfigFile.id == config_id).first()
        except Exception as e:
            raise Exception(f"获取数据库配置失败: {str(e)}")

    def create_config(self, config: ConfigFileCreate, user_id: str = "system") -> ConfigFile:
        try:
            # 使用当前时区的时间
            now = datetime.now(self.timezone)
            config_dict = config.dict()
            
            # 创建数据库模型
            db_config = DBConfigFile(
                name=config_dict['name'],
                template_type=config_dict['template_type'],
                content=config_dict['content'],
                description=config_dict.get('description'),
                device_type=config_dict.get('device_type', 'cisco_ios'),
                status=config_dict.get('status', 'draft'),
                created_at=now,
                updated_at=now
            )
            self.db.add(db_config)
            self.db.commit()
            self.db.refresh(db_config)
            
            # 确保返回的数据包含所有必需字段
            return ConfigFile(
                id=str(db_config.id),
                name=db_config.name,
                template_type=db_config.template_type,
                content=db_config.content,
                description=db_config.description,
                status=db_config.status,
                device_type=db_config.device_type,
                tags=config_dict.get('tags', []),
                created_at=db_config.created_at,
                updated_at=db_config.updated_at,
                created_by=user_id,
                updated_by=user_id
            )
        except Exception as e:
            self.db.rollback()
            raise Exception(f"创建配置失败: {str(e)}")

    def update_config(self, config_id: int, config: ConfigFileUpdate, user_id: str = "system") -> Optional[ConfigFile]:
        try:
            db_config = self._get_db_config(config_id)
            if db_config:
                # 将template_type映射到type字段，只保留数据库模型中存在的字段
                config_dict = config.dict()
                
                # 只更新数据库模型中存在的字段
                allowed_fields = ['name', 'template_type', 'content', 'description', 'device_type', 'status']
                for key, value in config_dict.items():
                    if key in allowed_fields:
                        if key == 'template_type':
                            setattr(db_config, 'template_type', value)
                        else:
                            setattr(db_config, key, value)
                # 使用当前时区的时间
                db_config.updated_at = datetime.now(self.timezone)
                self.db.commit()
                self.db.refresh(db_config)
                
                # 直接返回符合响应模型的数据
                return ConfigFile(
                    id=str(db_config.id),
                    name=db_config.name,
                    template_type=db_config.template_type,
                    content=db_config.content,
                    description=db_config.description,
                    status=db_config.status,
                    device_type=db_config.device_type,
                    tags=config_dict.get('tags', []),
                    created_at=db_config.created_at,
                    updated_at=db_config.updated_at,
                    created_by=user_id,
                    updated_by=user_id
                )
            return None
        except Exception as e:
            self.db.rollback()
            raise Exception(f"更新配置失败: {str(e)}")

    def delete_config(self, config_id: int) -> bool:
        try:
            db_config = self._get_db_config(config_id)
            if db_config:
                self.db.delete(db_config)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            raise Exception(f"删除配置失败: {str(e)}")

    def _convert_to_response_model(self, db_config: DBConfigFile) -> ConfigFile:
        """将数据库模型转换为响应模型"""
        return ConfigFile(
            id=str(db_config.id),
            name=db_config.name,
            template_type=db_config.template_type,
            content=db_config.content,
            description=db_config.description,
            status=db_config.status,
            device_type=db_config.device_type,
            tags=[],  # 从数据库获取标签
            created_at=db_config.created_at,
            updated_at=db_config.updated_at,
            created_by="system",  # 从数据库获取创建者
            updated_by="system"   # 从数据库获取更新者
        )

    def search_configs(
        self,
        name: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 10
    ) -> List[ConfigFile]:
        try:
            query = self.db.query(DBConfigFile)
            
            # 构建过滤条件
            filters = []
            
            if name:
                filters.append(DBConfigFile.name.ilike(f"%{name}%"))
            if device_type:
                filters.append(DBConfigFile.device_type == device_type)
            if status:
                filters.append(DBConfigFile.status == status)
            if start_date:
                filters.append(DBConfigFile.created_at >= start_date)
            if end_date:
                filters.append(DBConfigFile.created_at <= end_date)
            
            # 应用所有过滤条件
            if filters:
                query = query.filter(and_(*filters))
            
            # 应用分页
            query = query.offset(skip).limit(limit)
            
            # 执行查询
            db_configs = query.all()
            return [self._convert_to_response_model(config) for config in db_configs]
            
        except Exception as e:
            raise Exception(f"搜索配置失败: {str(e)}") 