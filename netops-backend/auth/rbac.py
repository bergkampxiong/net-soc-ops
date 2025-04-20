from fastapi import HTTPException
from functools import wraps

# 角色检查装饰器
def role_required(required_role):
    """
    装饰器：检查用户是否具有所需角色
    
    参数:
        required_role (str): 所需的角色名称
    
    返回:
        装饰器函数
    
    示例:
        @role_required("Admin")
        async def admin_only_endpoint(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="User not authenticated")
            
            if current_user.role != required_role:
                raise HTTPException(status_code=403, detail=f"Not authorized. Required role: {required_role}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 多角色检查装饰器
def roles_required(required_roles):
    """
    装饰器：检查用户是否具有所需角色之一
    
    参数:
        required_roles (list): 所需角色名称列表
    
    返回:
        装饰器函数
    
    示例:
        @roles_required(["Admin", "Operator"])
        async def admin_or_operator_endpoint(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                print(f"用户未认证，拒绝访问 {func.__name__}")
                raise HTTPException(status_code=401, detail="User not authenticated")
            
            print(f"用户 {current_user.username} 角色 {current_user.role} 尝试访问 {func.__name__}")
            print(f"所需角色: {', '.join(required_roles)}")
            
            if current_user.role not in required_roles:
                print(f"用户 {current_user.username} 角色 {current_user.role} 无权访问 {func.__name__}")
                raise HTTPException(status_code=403, detail=f"Not authorized. Required roles: {', '.join(required_roles)}")
            
            print(f"用户 {current_user.username} 角色 {current_user.role} 已授权访问 {func.__name__}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 权限检查函数
def has_permission(user, permission):
    """
    检查用户是否具有特定权限
    
    参数:
        user: 用户对象
        permission (str): 权限名称
    
    返回:
        bool: 是否具有权限
    """
    # 基于角色的权限映射
    role_permissions = {
        "admin": [
            "create_user", "disable_user", "reset_password", "toggle_2fa", 
            "view_audit_logs", "configure_ldap", "manage_system", "view_system",
            "manage_users", "manage_roles", "manage_security"
        ],
        "operator": ["view_users", "change_own_password"],
        "auditor": ["view_users", "view_audit_logs"]
    }
    
    # 检查用户角色是否具有所需权限
    if user.role in role_permissions and permission in role_permissions[user.role]:
        return True
    
    return False

# 权限检查装饰器
def permission_required(required_permission):
    """
    装饰器：检查用户是否具有所需权限
    
    参数:
        required_permission (str): 所需的权限名称
    
    返回:
        装饰器函数
    
    示例:
        @permission_required("create_user")
        async def create_user_endpoint(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="User not authenticated")
            
            if not has_permission(current_user, required_permission):
                raise HTTPException(status_code=403, detail=f"Not authorized. Required permission: {required_permission}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator 