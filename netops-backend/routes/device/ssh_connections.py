from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from database.session import get_db
from database.device_connection_models import DeviceConnection
from database.category_models import Credential
from schemas.device_connection import SSHConnectionCreate, SSHConnectionUpdate, SSHConnectionResponse
from datetime import datetime
from utils.datetime_utils import utc_to_beijing_str
from auth.authentication import get_current_user, get_current_user_optional

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/device/connections",
    tags=["device-connections"]
)


def _credential_id_to_int(credential_id) -> Optional[int]:
    """将 credential_id 转为 int 用于查询（Credential.id 为整型，DeviceConnection.credential_id 可能为字符串）"""
    if credential_id is None:
        return None
    if isinstance(credential_id, int):
        return credential_id
    try:
        return int(credential_id)
    except (TypeError, ValueError):
        return None


@router.get("/", response_model=List[SSHConnectionResponse])
async def get_device_connections(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user_optional),
):
    """获取所有SSH连接配置（不强制认证，始终返回全量列表，供设备连接页与流程设计器设备节点共用）"""
    try:
        connections = db.query(DeviceConnection).all()
        # 构造响应数据
        response_data = []
        for conn in connections:
            # 获取关联的凭证信息（credential_id 可能为字符串，需与 Credential.id 整型一致）
            cred_id = _credential_id_to_int(conn.credential_id)
            credential = db.query(Credential).filter(Credential.id == cred_id).first() if cred_id is not None else None
            if credential:
                username = credential.username
                password = credential.password
                enable_secret = credential.enable_password
            else:
                username = None
                password = None
                enable_secret = None

            response_data.append({
                "id": conn.id,
                "name": conn.name,
                "device_type": conn.device_type,
                "credential_id": str(conn.credential_id),  # 确保是字符串
                "port": conn.port,
                "enable_secret": enable_secret,  # 使用凭证中的enable_password
                "global_delay_factor": conn.global_delay_factor,
                "auth_timeout": conn.auth_timeout,
                "banner_timeout": conn.banner_timeout,
                "fast_cli": conn.fast_cli,
                "session_timeout": conn.session_timeout,
                "conn_timeout": conn.conn_timeout,
                "keepalive": conn.keepalive,
                "verbose": conn.verbose,
                "description": conn.description,
                "created_at": utc_to_beijing_str(conn.created_at) or utc_to_beijing_str(datetime.utcnow()) or "",
                "updated_at": utc_to_beijing_str(conn.updated_at) or utc_to_beijing_str(datetime.utcnow()) or "",
                "is_active": conn.is_active,
                "username": username,  # 使用凭证中的username
                "password": password   # 使用凭证中的password
            })
        return response_data
    except Exception as e:
        logger.error(f"获取SSH连接配置列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取SSH连接配置列表失败: {str(e)}"
        )

@router.post("/", response_model=SSHConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_device_connection(
    connection: SSHConnectionCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """创建新的SSH连接配置"""
    try:
        # 将device_type映射到system_type
        db_connection = DeviceConnection(
            name=connection.name,
            device_type=connection.device_type,
            credential_id=str(connection.credential_id),  # 转换为字符串
            port=connection.port,
            enable_secret=connection.enable_secret,
            global_delay_factor=connection.global_delay_factor,
            auth_timeout=connection.auth_timeout,
            banner_timeout=connection.banner_timeout,
            fast_cli=connection.fast_cli,
            session_timeout=connection.session_timeout,
            conn_timeout=connection.conn_timeout,
            keepalive=connection.keepalive,
            verbose=connection.verbose,
            description=connection.description,
            is_active=True
        )
        
        try:
            db.add(db_connection)
            db.commit()
            db.refresh(db_connection)
        except Exception as db_error:
            logger.error(f"数据库操作失败: {str(db_error)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"数据库操作失败: {str(db_error)}"
            )
        
        try:
            # 获取关联的凭证信息
            cred_id = _credential_id_to_int(db_connection.credential_id)
            credential = db.query(Credential).filter(Credential.id == cred_id).first() if cred_id is not None else None
            if credential:
                username = credential.username
                password = credential.password
                enable_secret = credential.enable_password
            else:
                username = None
                password = None
                enable_secret = None

            # 构造响应数据（时间使用全局时钟格式化）
            response_data = {
                "id": db_connection.id,
                "name": db_connection.name,
                "device_type": db_connection.device_type,
                "credential_id": str(db_connection.credential_id),  # 确保是字符串
                "port": db_connection.port,
                "enable_secret": enable_secret,  # 使用凭证中的enable_password
                "global_delay_factor": db_connection.global_delay_factor,
                "auth_timeout": db_connection.auth_timeout,
                "banner_timeout": db_connection.banner_timeout,
                "fast_cli": db_connection.fast_cli,
                "session_timeout": db_connection.session_timeout,
                "conn_timeout": db_connection.conn_timeout,
                "keepalive": db_connection.keepalive,
                "verbose": db_connection.verbose,
                "description": db_connection.description,
                "created_at": utc_to_beijing_str(db_connection.created_at) or utc_to_beijing_str(datetime.utcnow()) or "",
                "updated_at": utc_to_beijing_str(db_connection.updated_at) or utc_to_beijing_str(datetime.utcnow()) or "",
                "is_active": db_connection.is_active,
                "username": username,  # 使用凭证中的username
                "password": password   # 使用凭证中的password
            }
            return response_data
        except Exception as response_error:
            logger.error(f"构造响应数据失败: {str(response_error)}")
            # 即使响应构造失败，数据也已经保存到数据库中了
            now_str = utc_to_beijing_str(datetime.utcnow()) or ""
            return {
                "id": db_connection.id,
                "name": db_connection.name,
                "device_type": db_connection.device_type,
                "credential_id": str(db_connection.credential_id),
                "port": db_connection.port,
                "enable_secret": enable_secret,
                "global_delay_factor": db_connection.global_delay_factor,
                "auth_timeout": db_connection.auth_timeout,
                "banner_timeout": db_connection.banner_timeout,
                "fast_cli": db_connection.fast_cli,
                "session_timeout": db_connection.session_timeout,
                "conn_timeout": db_connection.conn_timeout,
                "keepalive": db_connection.keepalive,
                "verbose": db_connection.verbose,
                "description": db_connection.description,
                "is_active": db_connection.is_active,
                "created_at": now_str,
                "updated_at": now_str,
                "username": username,
                "password": password
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建设备连接配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建设备连接配置失败: {str(e)}"
        )

@router.get("/{connection_id}", response_model=SSHConnectionResponse)
async def get_device_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取单个SSH连接配置"""
    try:
        connection = db.query(DeviceConnection).filter(DeviceConnection.id == connection_id).first()
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSH连接配置 {connection_id} 不存在"
            )

        # 获取关联的凭证信息
        cred_id = _credential_id_to_int(connection.credential_id)
        credential = db.query(Credential).filter(Credential.id == cred_id).first() if cred_id is not None else None
        if credential:
            username = credential.username
            password = credential.password
            enable_secret = credential.enable_password
        else:
            username = None
            password = None
            enable_secret = None

        # 构造响应数据（时间使用全局时钟格式化）
        response_data = {
            "id": connection.id,
            "name": connection.name,
            "device_type": connection.device_type,
            "credential_id": str(connection.credential_id),
            "port": connection.port,
            "enable_secret": enable_secret,  # 使用凭证中的enable_password
            "global_delay_factor": connection.global_delay_factor,
            "auth_timeout": connection.auth_timeout,
            "banner_timeout": connection.banner_timeout,
            "fast_cli": connection.fast_cli,
            "session_timeout": connection.session_timeout,
            "conn_timeout": connection.conn_timeout,
            "keepalive": connection.keepalive,
            "verbose": connection.verbose,
            "description": connection.description,
            "created_at": utc_to_beijing_str(connection.created_at) or utc_to_beijing_str(datetime.utcnow()) or "",
            "updated_at": utc_to_beijing_str(connection.updated_at) or utc_to_beijing_str(datetime.utcnow()) or "",
            "is_active": connection.is_active,
            "username": username,  # 使用凭证中的username
            "password": password   # 使用凭证中的password
        }
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取SSH连接配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取SSH连接配置失败: {str(e)}"
        )

@router.put("/{connection_id}", response_model=SSHConnectionResponse)
async def update_device_connection(
    connection_id: int,
    connection_update: SSHConnectionUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """更新SSH连接配置"""
    try:
        db_connection = db.query(DeviceConnection).filter(DeviceConnection.id == connection_id).first()
        if not db_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSH连接配置 {connection_id} 不存在"
            )
        
        # 更新字段
        update_data = connection_update.dict(exclude_unset=True)
        
        # 如果更新包含credential_id，确保转换为字符串
        if 'credential_id' in update_data:
            update_data['credential_id'] = str(update_data['credential_id'])
            
        for field, value in update_data.items():
            setattr(db_connection, field, value)
        
        db.commit()
        db.refresh(db_connection)

        # 获取关联的凭证信息
        cred_id = _credential_id_to_int(db_connection.credential_id)
        credential = db.query(Credential).filter(Credential.id == cred_id).first() if cred_id is not None else None
        if credential:
            username = credential.username
            password = credential.password
            enable_secret = credential.enable_password
        else:
            username = None
            password = None
            enable_secret = None

        # 构造响应数据
        response_data = {
            "id": db_connection.id,
            "name": db_connection.name,
            "device_type": db_connection.device_type,
            "credential_id": str(db_connection.credential_id),
            "port": db_connection.port,
            "enable_secret": enable_secret,  # 使用凭证中的enable_password
            "global_delay_factor": db_connection.global_delay_factor,
            "auth_timeout": db_connection.auth_timeout,
            "banner_timeout": db_connection.banner_timeout,
            "fast_cli": db_connection.fast_cli,
            "session_timeout": db_connection.session_timeout,
            "conn_timeout": db_connection.conn_timeout,
            "keepalive": db_connection.keepalive,
            "verbose": db_connection.verbose,
            "description": db_connection.description,
            "created_at": utc_to_beijing_str(db_connection.created_at) or utc_to_beijing_str(datetime.utcnow()) or "",
            "updated_at": utc_to_beijing_str(db_connection.updated_at) or utc_to_beijing_str(datetime.utcnow()) or "",
            "is_active": db_connection.is_active,
            "username": username,  # 使用凭证中的username
            "password": password   # 使用凭证中的password
        }
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新SSH连接配置失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新SSH连接配置失败: {str(e)}"
        )

@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """删除SSH连接配置"""
    try:
        db_connection = db.query(DeviceConnection).filter(DeviceConnection.id == connection_id).first()
        if not db_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSH连接配置 {connection_id} 不存在"
            )
        
        db.delete(db_connection)
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除SSH连接配置失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除SSH连接配置失败: {str(e)}"
        ) 