import json
import urllib.parse
import ldap
from typing import Dict, Any

def parse_ldap_url(url: str) -> Dict[str, Any]:
    """解析LDAP URL"""
    try:
        # 移除可能的ldap://或ldaps://前缀
        url = url.replace('ldap://', '').replace('ldaps://', '')
        
        # 分离主机和端口
        if ':' in url:
            host, port = url.split(':')
            port = int(port)
        else:
            host = url
            port = 389  # 默认LDAP端口
        
        return {
            'host': host,
            'port': port
        }
    except Exception as e:
        raise ValueError(f"无效的LDAP URL格式: {str(e)}")

def test_ldap_connection(server_url: str, bind_dn: str, bind_password: str, search_base: str, use_ssl: bool = False) -> dict:
    """测试LDAP连接"""
    try:
        # 解析服务器地址
        if not server_url.startswith(('ldap://', 'ldaps://')):
            server_url = f"ldap://{server_url}"
        
        # 处理绑定DN中的特殊字符
        # 如果绑定DN包含特殊字符，尝试不同的格式
        bind_dn_formats = [
            bind_dn,  # 原始格式
            bind_dn.replace('"', '\\"'),  # 转义双引号
            bind_dn.replace(' ', '\\ '),  # 转义空格
            f'"{bind_dn}"',  # 用双引号包围
            bind_dn.replace('(', '\\(').replace(')', '\\)'),  # 转义括号
            bind_dn.replace(',', '\\,'),  # 转义逗号
            bind_dn.replace('+', '\\+'),  # 转义加号
            bind_dn.replace('=', '\\='),  # 转义等号
            bind_dn.replace('<', '\\<').replace('>', '\\>'),  # 转义尖括号
            bind_dn.replace(';', '\\;'),  # 转义分号
            bind_dn.replace('\\', '\\\\'),  # 转义反斜杠
            bind_dn.replace('#', '\\#'),  # 转义井号
            bind_dn.replace('-', '\\-'),  # 转义连字符
        ]
        
        # 处理密码中的特殊字符
        # 如果密码包含特殊字符，尝试不同的格式
        password_formats = [
            bind_password,  # 原始格式
            bind_password.replace('"', '\\"'),  # 转义双引号
            bind_password.replace('\\', '\\\\'),  # 转义反斜杠
            f'"{bind_password}"',  # 用双引号包围
        ]
        
        # 创建LDAP连接
        if use_ssl:
            conn = ldap.initialize(f"ldaps://{server_url.replace('ldap://', '').replace('ldaps://', '')}")
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        else:
            conn = ldap.initialize(f"ldap://{server_url.replace('ldap://', '').replace('ldaps://', '')}")
        
        # 设置连接选项
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        
        # 尝试不同的绑定DN和密码格式
        connected = False
        error_message = ""
        
        for bind_dn_format in bind_dn_formats:
            if connected:
                break
                
            for password_format in password_formats:
                try:
                    # 尝试绑定
                    conn.simple_bind_s(bind_dn_format, password_format)
                    
                    # 测试搜索
                    search_filter = '(objectClass=*)'
                    search_scope = ldap.SCOPE_BASE
                    search_attrs = ['objectClass']
                    
                    result = conn.search_s(
                        search_base,
                        search_scope,
                        search_filter,
                        search_attrs
                    )
                    
                    # 如果成功，标记为已连接
                    connected = True
                    break
                except ldap.INVALID_CREDENTIALS:
                    error_message = "LDAP认证失败：用户名或密码错误"
                    continue
                except ldap.SERVER_DOWN:
                    error_message = "LDAP连接被拒绝"
                    continue
                except Exception as e:
                    error_message = f"LDAP连接测试失败: {str(e)}"
                    continue
        
        # 关闭连接
        conn.unbind_s()
        
        if connected:
            return {
                "success": True,
                "message": "LDAP连接测试成功",
                "server_info": {
                    "server_url": server_url,
                    "bind_dn": bind_dn,
                    "search_base": search_base,
                    "use_ssl": use_ssl
                }
            }
        else:
            return {
                "success": False,
                "message": error_message
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"LDAP连接测试失败: {str(e)}"
        } 