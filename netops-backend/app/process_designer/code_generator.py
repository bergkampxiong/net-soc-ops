from typing import Dict, List, Any
from netmiko import ConnectHandler
from utils.device_connection_manager import DeviceConnectionManager
import logging

# 设备类型 -> 默认配置备份命令（与前端 sshConfig deviceTypes 对齐，含 huawei_vrpv8 等）
BACKUP_CMD_MAP = {
    'cisco_ios': 'show running-config', 'cisco_xe': 'show running-config',
    'cisco_nxos': 'show running-config', 'cisco_xr': 'show running-config',
    'huawei': 'display current-configuration', 'huawei_vrp': 'display current-configuration',
    'huawei_vrpv8': 'display current-configuration',
    'h3c': 'display current-configuration', 'hp_comware': 'display current-configuration',
    'paloalto_panos': 'show config running', 'ruijie': 'show running-config',
    'ruijie_os': 'show running-config', 'fortinet': 'get system running-config',
    'linux': 'cat /etc/config/* 2>/dev/null || true',
}

class CodeGenerator:
    def __init__(self, process_definition: Dict[str, Any]):
        self.process_definition = process_definition
        self.nodes = process_definition.get('nodes', [])
        self.edges = process_definition.get('edges', [])

    def validate(self) -> Dict[str, Any]:
        """验证流程定义的有效性"""
        errors = []
        
        # 检查必要的节点
        start_nodes = [node for node in self.nodes if node['type'] == 'start']
        if len(start_nodes) != 1:
            errors.append('流程必须包含一个开始节点')
            
        end_nodes = [node for node in self.nodes if node['type'] == 'end']
        if len(end_nodes) != 1:
            errors.append('流程必须包含一个结束节点')
            
        # 检查设备连接节点
        device_nodes = [node for node in self.nodes if node['type'] == 'deviceConnect']
        if not device_nodes:
            errors.append('流程必须包含至少一个设备连接节点')
            
        # 至少需要配置下发或配置备份之一
        config_deploy_nodes = [node for node in self.nodes if node['type'] == 'configDeploy']
        config_backup_nodes = [node for node in self.nodes if node['type'] == 'configBackup']
        if not config_deploy_nodes and not config_backup_nodes:
            errors.append('流程必须包含至少一个配置下发节点或配置备份节点')
        return {
            'isValid': len(errors) == 0,
            'errors': errors
        }

    def generate_code(self) -> str:
        """生成Python代码"""
        # 从流程定义中提取设备连接信息
        def _device_type(ssh_cfg: dict) -> str:
            """从 sshConfig 读取设备类型，兼容 device_type / deviceType"""
            return (ssh_cfg or {}).get("device_type") or (ssh_cfg or {}).get("deviceType") or ""

        def _secret(ssh_cfg: dict) -> str:
            """从 sshConfig 读取 enable secret，兼容 snake_case / camelCase"""
            return (ssh_cfg or {}).get("enable_secret") or (ssh_cfg or {}).get("enableSecret") or ""

        device_nodes = [node for node in self.nodes if node['type'] == 'deviceConnect']
        device_list = []
        for node in device_nodes:
            device_config = node.get('data') or {}
            ssh_config = device_config.get('sshConfig') or {}
            selected_devices = device_config.get('selectedDevices') or []
            dt = _device_type(ssh_config)
            for device_ip in selected_devices:
                device_info = {
                    "name": device_ip,
                    "device_type": dt,
                    "host": device_ip,
                    "port": ssh_config.get("port", 22),
                    "username": ssh_config.get("username", ""),
                    "password": ssh_config.get("password", ""),
                    "secret": _secret(ssh_config),
                }
                device_list.append(device_info)

        # 配置备份：确定备份设备列表与备注
        config_backup_nodes = [n for n in self.nodes if n.get('type') == 'configBackup']
        backup_device_list = []
        backup_remark = ''
        backup_cmd_override = ''
        if config_backup_nodes:
            backup_node = config_backup_nodes[0]
            backup_remark = (backup_node.get('data') or {}).get('remark') or ''
            backup_cmd_override = (backup_node.get('data') or {}).get('backupCommand') or ''
            use_node_id = (backup_node.get('data') or {}).get('useDeviceFromNodeId')
            dev_node = next((n for n in device_nodes if n.get('id') == use_node_id), None) if use_node_id else (device_nodes[0] if device_nodes else None)
            if dev_node:
                dc = dev_node.get('data') or {}
                ssh_config = dc.get('sshConfig') or {}
                dt = _device_type(ssh_config)
                for device_ip in dc.get('selectedDevices') or []:
                    backup_device_list.append({
                        'name': device_ip,
                        'device_type': dt,
                        'host': device_ip,
                        'port': ssh_config.get('port', 22),
                        'username': ssh_config.get('username', ''),
                        'password': ssh_config.get('password', ''),
                        'secret': _secret(ssh_config),
                    })
        # 若备份设备未从连接节点读到 device_type，尝试从 device_list（同 host）补齐
        host_to_device_type = {d['host']: d['device_type'] for d in device_list if d.get('device_type')}
        for d in backup_device_list:
            if not d.get('device_type') and d.get('host') in host_to_device_type:
                d['device_type'] = host_to_device_type[d['host']]
        # 连接用设备列表：下发用 + 备份用（按 host 去重）
        seen_hosts = {d['host'] for d in device_list}
        all_devices = list(device_list)
        for d in backup_device_list:
            if d['host'] not in seen_hosts:
                seen_hosts.add(d['host'])
                all_devices.append(d)

        # 从流程定义中提取配置内容
        config_nodes = [node for node in self.nodes if node['type'] == 'configDeploy']
        config_content = []
        if config_nodes:
            config_data = config_nodes[0]['data']
            config_content = config_data.get('configContent', '').splitlines()

        # 生成代码
        code = [
            '#!/usr/bin/env python',
            '# -*- coding: utf-8 -*-',
            '',
            'import os',
            'import requests',
            'from typing import Dict, List, Any',
            'from netmiko import ConnectHandler',
            '',
            'class ProcessExecutor:',
            '    def __init__(self):',
            '        self.config_module_base_url = os.environ.get("CONFIG_MODULE_API_URL", "http://127.0.0.1:8000/api")',
            '        # 设备信息列表（连接用）',
            '        self.device_list = [',
        ]

        # 添加设备列表（all_devices）
        for device in all_devices:
            code.extend([
                '            {',
                f'                "name": "{device["name"]}",',
                f'                "device_type": "{device["device_type"]}",',
                f'                "host": "{device["host"]}",',
                f'                "port": {device["port"]},',
                f'                "username": "{device["username"]}",',
                f'                "password": "{device["password"]}",',
                f'                "secret": "{device["secret"]}"',
                '            },',
            ])

        code.extend([
            '        ]',
            '        # 配置备份设备列表（仅备份时使用）',
            '        self.backup_device_list = [',
        ])
        for device in backup_device_list:
            code.extend([
                '            {',
                f'                "name": "{device["name"]}",',
                f'                "device_type": "{device["device_type"]}",',
                f'                "host": "{device["host"]}",',
                '            },',
            ])
        code.extend([
            '        ]',
            '        self.backup_remark = ' + repr(backup_remark) + '  # 配置备份节点备注',
            '',
            '        self.backup_cmd_override = ' + repr(backup_cmd_override) + '  # 覆盖时用此命令',
            '',
            '        # 公共连接参数',
            '        self.common_params = {',
            '            "global_delay_factor": 1,',
            '            "auth_timeout": 20,',
            '            "banner_timeout": 20,',
            '            "fast_cli": False,',
            '            "session_timeout": 60,',
            '            "conn_timeout": 10,',
            '            "keepalive": 10,',
            '            "verbose": False',
            '        }',
            '        # 公共配置内容',
            '        self.config = [',
        ])

        # 添加配置内容
        for line in config_content:
            if line.strip():  # 跳过空行
                code.append(f'            "{line}",')

        code.extend([
            '        ]',
            '',
            '    def execute(self):',
            '        connections = {}',
            '        try:',
            '            connections = self._connect_devices()',
            '            if self.backup_device_list:',
            '                self._backup_configs(connections)',
            '            if self.config:',
            '                self._deploy_configs(connections)',
            '        finally:',
            '            self._close_connections(connections)',
            '',
            '    def _report_connection(self, event: str):',
            '        """上报连接事件，供连接池监控页统计（作业执行时也会更新）。"""',
            '        try:',
            '            url = f"{self.config_module_base_url.rstrip(\'/\')}/device/connections/pools/report"',
            '            requests.post(url, json={"event": event}, timeout=5)',
            '        except Exception:',
            '            pass',
            '',
            '    def _connect_devices(self) -> Dict[str, Any]:',
            '        connections = {}',
            '        for device_info in self.device_list:',
            '            device_params = {**device_info, **self.common_params}',
            '            name = device_params.pop("name", device_info["name"])',
            '            try:',
            '                connection = ConnectHandler(**device_params)',
            '                connections[name] = connection',
            '                self._report_connection("connect")',
            '            except Exception as e:',
            '                print(f"连接设备 {name} 失败: {str(e)}")',
            '        if not connections:',
            '            raise Exception("所有设备连接失败")',
            '        return connections',
            '',
            '    def _backup_configs(self, connections: Dict[str, Any]):',
            '        backup_cmd_map = {"cisco_ios": "show running-config", "cisco_xe": "show running-config", "cisco_nxos": "show running-config", "cisco_xr": "show running-config", "huawei": "display current-configuration", "huawei_vrp": "display current-configuration", "huawei_vrpv8": "display current-configuration", "h3c": "display current-configuration", "hp_comware": "display current-configuration", "paloalto_panos": "show config running", "ruijie": "show running-config", "ruijie_os": "show running-config", "fortinet": "get system running-config", "linux": "cat /etc/config/* 2>/dev/null || true"}',
            '        def _backup_cmd(dt):',
            '            if backup_cmd_map.get(dt): return backup_cmd_map[dt]',
            '            if (dt or "").startswith("huawei"): return "display current-configuration"',
            '            if (dt or "").startswith("cisco"): return "show running-config"',
            '            return "show running-config"',
            '        for dev in self.backup_device_list:',
            '            name = dev["name"]',
            '            conn = connections.get(name)',
            '            if not conn:',
            '                print(f"备份跳过 {name}: 无连接")',
            '                continue',
            '            cmd = self.backup_cmd_override or _backup_cmd(dev.get("device_type", ""))',
            '            try:',
            '                print(f"设备 {name} 备份命令执行中（delay_factor=3, max_loops=600，预计等待时间较长）...")',
            '                content = conn.send_command(cmd, delay_factor=3, max_loops=600)',
            '                if not content or (len(content.strip()) < 500 and ("Unrecognized command" in content or "Error:" in content or "% Invalid" in content or "% Error" in content)):',
            '                    print(f"设备 {name} 备份跳过: 输出疑似设备报错而非配置，请检查设备类型与备份命令")',
            '                    continue',
            '                url = f"{self.config_module_base_url.rstrip(\'/\')}/config-module/backups"',
            '                r = requests.post(url, json={"device_id": name, "device_host": name, "device_name": "", "content": content, "source": "workflow", "remark": self.backup_remark or ""}, timeout=30)',
            '                r.raise_for_status()',
            '                print(f"设备 {name} 配置备份已上报")',
            '            except Exception as e:',
            '                print(f"设备 {name} 配置备份失败: {str(e)}")',
            '',
            '    def _deploy_configs(self, connections: Dict[str, Any]):',
            '        for name, connection in connections.items():',
            '            try:',
            '                output = connection.send_config_set(self.config)',
            '                print(f"设备 {name} 配置下发成功: {output}")',
            '                connection.save_config()',
            '            except Exception as e:',
            '                print(f"设备 {name} 配置下发失败: {str(e)}")',
            '',
            '    def _close_connections(self, connections: Dict[str, Any]):',
            '        for name, connection in connections.items():',
            '            try:',
            '                self._report_connection("disconnect")',
            '                connection.disconnect()',
            '            except Exception as e:',
            '                print(f"关闭设备 {name} 连接失败: {str(e)}")',
            '',
            'if __name__ == "__main__":',
            '    executor = ProcessExecutor()',
            '    executor.execute()',
        ])

        return '\n'.join(code) 