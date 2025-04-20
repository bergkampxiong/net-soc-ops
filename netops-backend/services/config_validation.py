import re
from typing import List, Dict, Optional
import difflib

class ConfigValidationService:
    def __init__(self):
        self.device_validators = {
            'cisco_ios': self.validate_cisco_ios,
            'huawei_vrp': self.validate_huawei_vrp,
            # 其他设备类型的验证器
        }

    def validate_config(self, content: str, device_type: str) -> List[Dict]:
        """验证配置内容"""
        validator = self.device_validators.get(device_type)
        if not validator:
            return []
        return validator(content)

    def validate_cisco_ios(self, content: str) -> List[Dict]:
        """验证Cisco IOS配置"""
        errors = []
        lines = content.split('\n')
        interface_pattern = re.compile(r'^interface\s+(\S+)')
        ip_pattern = re.compile(r'ip\s+address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
        
        for i, line in enumerate(lines):
            # 检查接口配置
            if interface_match := interface_pattern.match(line):
                interface_name = interface_match.group(1)
                if not self._is_valid_interface_name(interface_name):
                    errors.append({
                        'line': i + 1,
                        'message': f'Invalid interface name: {interface_name}',
                        'severity': 'error'
                    })
            
            # 检查IP地址配置
            if ip_match := ip_pattern.match(line):
                ip, mask = ip_match.groups()
                if not self._is_valid_ip(ip) or not self._is_valid_ip(mask):
                    errors.append({
                        'line': i + 1,
                        'message': 'Invalid IP address or subnet mask',
                        'severity': 'error'
                    })
        
        return errors

    def validate_huawei_vrp(self, content: str) -> List[Dict]:
        """验证华为VRP配置"""
        errors = []
        lines = content.split('\n')
        # 实现华为设备的配置验证逻辑
        return errors

    def _is_valid_interface_name(self, name: str) -> bool:
        """验证接口名称"""
        valid_patterns = [
            r'^GigabitEthernet\d+/\d+(/\d+)?$',
            r'^FastEthernet\d+/\d+(/\d+)?$',
            r'^Loopback\d+$',
            r'^Vlan\d+$'
        ]
        return any(re.match(pattern, name) for pattern in valid_patterns)

    def _is_valid_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except (AttributeError, TypeError, ValueError):
            return False

    def format_config(self, content: str, device_type: str) -> str:
        """格式化配置内容"""
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            line = line.strip()
            
            # 减少缩进级别的命令
            if line in ['end', 'exit', 'quit', '!']:
                indent_level = max(0, indent_level - 1)
            
            # 添加适当的缩进
            if line and not line.startswith('!'):
                formatted_lines.append('  ' * indent_level + line)
            else:
                formatted_lines.append(line)
            
            # 增加缩进级别的命令
            if line.startswith(('interface', 'router', 'policy-map', 'class-map')):
                indent_level += 1
        
        return '\n'.join(formatted_lines)

    def compare_versions(self, original: str, modified: str) -> List[Dict]:
        """比较两个版本的配置"""
        diff = list(difflib.unified_diff(
            original.splitlines(),
            modified.splitlines(),
            lineterm=''
        ))
        
        changes = []
        for line in diff:
            if line.startswith('+'):
                changes.append({
                    'type': 'addition',
                    'content': line[1:],
                })
            elif line.startswith('-'):
                changes.append({
                    'type': 'deletion',
                    'content': line[1:],
                })
            elif line.startswith('@@'):
                changes.append({
                    'type': 'header',
                    'content': line,
                })
        
        return changes 