from typing import List
from sqlalchemy.orm import Session
from database.config_management_models import ConfigFile as DBConfigFile
from schemas.config_management import ConfigFile

class ConfigGeneratorService:
    def __init__(self, db: Session):
        self.db = db

    def get_jinja2_templates(self) -> List[ConfigFile]:
        """获取所有jinja2类型的模板"""
        try:
            # 直接查询jinja2类型的模板
            db_configs = self.db.query(DBConfigFile).filter(
                DBConfigFile.template_type == 'jinja2'
            ).all()
            
            # 转换为响应模型
            return [self._convert_to_response_model(config) for config in db_configs]
        except Exception as e:
            raise Exception(f"获取jinja2模板列表失败: {str(e)}")

    def _convert_to_response_model(self, db_config: DBConfigFile) -> ConfigFile:
        """将数据库模型转换为响应模型"""
        try:
            return ConfigFile(
                id=str(db_config.id),
                name=db_config.name,
                template_type=db_config.template_type,
                content=db_config.content,
                description=db_config.description,
                status=db_config.status,
                device_type=db_config.device_type,
                tags=[],
                created_at=db_config.created_at,
                updated_at=db_config.updated_at,
                created_by="system",
                updated_by="system"
            )
        except Exception as e:
            raise Exception(f"转换响应模型失败: {str(e)}") 