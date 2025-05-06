from typing import Dict, List, Any
from netmiko import ConnectHandler
from utils.device_connection_manager import DeviceConnectionManager
import logging

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
            
        # 检查配置下发节点
        config_nodes = [node for node in self.nodes if node['type'] == 'configDeploy']
        if not config_nodes:
            errors.append('流程必须包含至少一个配置下发节点')
            
        return {
            'isValid': len(errors) == 0,
            'errors': errors
        }

    def generate_code(self) -> str:
        """生成Python代码"""
        # 从流程定义中提取设备连接信息
        device_nodes = [node for node in self.nodes if node['type'] == 'deviceConnect']
        device_list = []
        for node in device_nodes:
            device_config = node['data']
            ssh_config = device_config.get('sshConfig', {})
            selected_devices = device_config.get('selectedDevices', [])
            
            for device_ip in selected_devices:
                device_info = {
                    "name": device_ip,
                    "device_type": ssh_config.get("device_type", ""),
                    "host": device_ip,
                    "port": ssh_config.get("port", 22),
                    "username": ssh_config.get("username", ""),
                    "password": ssh_config.get("password", ""),
                    "secret": ssh_config.get("enable_secret", "")
                }
                device_list.append(device_info)

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
            'from typing import Dict, List, Any',
            'from netmiko import ConnectHandler',
            'from utils.device_connection_manager import DeviceConnectionManager',
            '',
            'class ProcessExecutor:',
            '    def __init__(self):',
            '        self.connection_manager = DeviceConnectionManager()',
            '        # 设备信息列表，便于批量扩展',
            '        self.device_list = [',
        ]

        # 添加设备列表
        for device in device_list:
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
            '            # 连接所有设备',
            '            connections = self._connect_devices()',
            '            # 下发配置',
            '            self._deploy_configs(connections)',
            '        finally:',
            '            # 关闭所有连接',
            '            self._close_connections(connections)',
            '',
            '    def _connect_devices(self) -> Dict[str, Any]:',
            '        connections = {}',
            '        for device_info in self.device_list:',
            '            device_params = {**device_info, **self.common_params}',
            '            try:',
            '                connection = self.connection_manager.get_connection(device_params)',
            '                connections[device_info["name"]] = connection',
            '            except Exception as e:',
            '                print(f"连接设备 {device_info[\'name\']} 失败: {str(e)}")',
            '        if not connections:',
            '            raise Exception("所有设备连接失败")',
            '        return connections',
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
            '                self.connection_manager.release_connection(connection)',
            '            except Exception as e:',
            '                print(f"关闭设备 {name} 连接失败: {str(e)}")',
            '',
            'if __name__ == "__main__":',
            '    executor = ProcessExecutor()',
            '    executor.execute()',
        ])

        return '\n'.join(code) 