from ldap3 import Server, Connection, ALL, SIMPLE
from sqlalchemy.orm import Session
from datetime import datetime
import json
import ldap
from typing import Tuple, Optional

from database.models import User, LDAPConfig

def get_ldap_config(db: Session):
    """获取LDAP配置"""
    return db.query(LDAPConfig).first()

def ldap_authenticate(username: str, password: str, db: Session) -> Tuple[Optional[User], Optional[str]]:
    """
    验证LDAP用户凭据
    
    Args:
        username: 用户名
        password: 密码
        db: 数据库会话
        
    Returns:
        Tuple[Optional[User], Optional[str]]: (用户对象, 错误信息)
    """
    try:
        # 获取LDAP配置
        ldap_config = db.query(LDAPConfig).first()
        if not ldap_config:
            return None, "LDAP未配置"
            
        # 解析服务器URL
        server_url = ldap_config.server_url
        if not server_url.startswith(('ldap://', 'ldaps://')):
            server_url = f"ldap://{server_url}"
            
        # 创建LDAP连接
        conn = ldap.initialize(server_url)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        
        # 设置连接选项
        if server_url.startswith('ldaps://'):
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            conn.start_tls_s()
        
        # 尝试绑定
        try:
            # 处理特殊字符
            bind_dn = ldap_config.bind_dn
            # 转义特殊字符
            special_chars = ['"', ' ', '(', ')', ',', '+', '=', '<', '>', ';', '\\', '#', '-']
            for char in special_chars:
                if char in bind_dn:
                    bind_dn = bind_dn.replace(char, f'\\{char}')
            
            # 尝试不同的bind_dn格式
            bind_dn_formats = [
                bind_dn,
                bind_dn.replace('\\', ''),
                f"cn={bind_dn}",
                f"uid={bind_dn}",
                f"cn={bind_dn},{ldap_config.search_base}"
            ]
            
            bind_success = False
            for bind_dn_format in bind_dn_formats:
                try:
                    conn.simple_bind_s(bind_dn_format, ldap_config.bind_password)
                    bind_success = True
                    break
                except ldap.INVALID_CREDENTIALS:
                    continue
                except Exception as e:
                    print(f"尝试bind_dn格式 {bind_dn_format} 失败: {str(e)}")
                    continue
            
            if not bind_success:
                return None, "LDAP绑定失败：无效的凭据"
                
        except ldap.SERVER_DOWN:
            return None, "LDAP服务器连接失败"
        except Exception as e:
            return None, f"LDAP绑定失败：{str(e)}"
            
        # 构建搜索过滤器
        search_filter = f"(&(objectClass=person)(sAMAccountName={username}))"
        
        # 执行搜索
        try:
            result = conn.search_s(
                ldap_config.search_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                ['dn', 'sAMAccountName', 'mail', 'department']
            )
        except Exception as e:
            return None, f"LDAP搜索失败：{str(e)}"
            
        if not result:
            return None, "用户不存在"
            
        # 获取用户DN
        user_dn = result[0][0]
        
        # 尝试使用用户凭据绑定
        try:
            conn.simple_bind_s(user_dn, password)
        except ldap.INVALID_CREDENTIALS:
            return None, "用户名或密码错误"
        except Exception as e:
            return None, f"用户认证失败：{str(e)}"
            
        # 获取用户邮箱和部门
        user_attrs = result[0][1]
        email = user_attrs.get('mail', [b''])[0].decode('utf-8') if user_attrs.get('mail') else None
        department = user_attrs.get('department', [b''])[0].decode('utf-8') if user_attrs.get('department') else None
        
        # 查找或创建用户
        user = db.query(User).filter(User.username == username).first()
        if not user:
            # 创建新用户时，默认设置为operator角色
            user = User(
                username=username,
                email=email,
                department=department,
                is_ldap_user=True,
                role="operator",  # 默认角色
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # 更新现有用户的信息，但保持原有角色不变
            user.email = email
            user.department = department
            db.commit()
            db.refresh(user)
            
        return user, None
        
    except Exception as e:
        return None, f"LDAP认证失败：{str(e)}"
    finally:
        try:
            conn.unbind_s()
        except:
            pass 