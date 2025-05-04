from typing import Dict, List, Any
from netmiko import ConnectHandler
from utils.connection_pool_manager import ConnectionPoolManager

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
        code = [
            '#!/usr/bin/env python',
            '# -*- coding: utf-8 -*-',
            '',
            'from typing import Dict, List, Any',
            'from netmiko import ConnectHandler',
            'from utils.connection_pool_manager import ConnectionPoolManager',
            '',
            'class ProcessExecutor:',
            '    def __init__(self):',
            '        self.connection_pool = ConnectionPoolManager()',
            '',
            '    def execute(self):',
            '        try:',
            '            # 设备连接',
            '            connections = self._connect_devices()',
            '',
            '            # 执行配置下发',
            '            self._deploy_configs(connections)',
            '',
            '        finally:',
            '            # 关闭所有连接',
            '            self._close_connections(connections)',
            '',
            '    def _connect_devices(self) -> Dict[str, Any]:',
            '        connections = {}',
            '        try:',
        ]

        # 添加设备连接代码
        device_nodes = [node for node in self.nodes if node['type'] == 'deviceConnect']
        for node in device_nodes:
            device_config = node['data']
            ssh_config = device_config.get('sshConfig', {})
            selected_devices = device_config.get('selectedDevices', [])
            
            for device_ip in selected_devices:
                code.extend([
                    f'            # 连接设备 {device_ip}',
                    '            try:',
                    '                device = {',
                    f'                    "device_type": "{ssh_config.get("device_type", "")}",',
                    f'                    "host": "{device_ip}",',
                    f'                    "port": {ssh_config.get("port", 22)},',
                    f'                    "username": "{ssh_config.get("username", "")}",',
                    f'                    "password": "{ssh_config.get("password", "")}",',
                    f'                    "global_delay_factor": {ssh_config.get("global_delay_factor", 1)},',
                    f'                    "auth_timeout": {ssh_config.get("auth_timeout", 20)},',
                    f'                    "banner_timeout": {ssh_config.get("banner_timeout", 20)},',
                    f'                    "fast_cli": {ssh_config.get("fast_cli", False)},',
                    f'                    "session_timeout": {ssh_config.get("session_timeout", 60)},',
                    f'                    "conn_timeout": {ssh_config.get("conn_timeout", 10)},',
                    f'                    "keepalive": {ssh_config.get("keepalive", 10)},',
                    f'                    "verbose": {ssh_config.get("verbose", False)}',
                    '                }',
                    '',
                    '                # 如果是思科设备，添加enable密码',
                    '                if device["device_type"].startswith("cisco_"):',
                    f'                    device["secret"] = "{ssh_config.get("enable_secret", "")}"',
                    '',
                    '                connection = self.connection_pool.get_connection(device)',
                    f'                connections["{device_ip}"] = connection',
                    '            except Exception as e:',
                    f'                print(f"连接设备 {device_ip} 失败: {{str(e)}}")',
                    '                raise',
                ])

        code.extend([
            '            return connections',
            '        except Exception as e:',
            '            print(f"设备连接失败: {str(e)}")',
            '            raise',
            '',
            '    def _deploy_configs(self, connections: Dict[str, Any]):',
            '        try:',
        ])

        # 添加配置下发代码
        config_nodes = [node for node in self.nodes if node['type'] == 'configDeploy']
        for node in config_nodes:
            config_data = node['data']
            config_content = config_data.get('configContent', '')
            
            # 获取需要下发配置的设备列表
            device_nodes = [node for node in self.nodes if node['type'] == 'deviceConnect']
            selected_devices = []
            for device_node in device_nodes:
                selected_devices.extend(device_node['data'].get('selectedDevices', []))
            
            for device_ip in selected_devices:
                code.extend([
                    f'            # 下发配置到设备 {device_ip}',
                    '            try:',
                    f'                connection = connections["{device_ip}"]',
                    f'                config = """{config_content}"""',
                    '',
                    '                # 下发配置',
                    '                output = connection.send_config_set(config.splitlines())',
                    '                print(f"配置下发成功: {output}")',
                    '',
                    '                # 保存配置',
                    '                connection.save_config()',
                    '            except Exception as e:',
                    f'                print(f"配置下发失败: {{str(e)}}")',
                    '                raise',
                ])

        code.extend([
            '        except Exception as e:',
            '            print(f"配置下发失败: {str(e)}")',
            '            raise',
            '',
            '    def _close_connections(self, connections: Dict[str, Any]):',
            '        for name, connection in connections.items():',
            '            try:',
            '                self.connection_pool.release_connection(connection)',
            '            except Exception as e:',
            '                print(f"关闭设备 {name} 连接失败: {str(e)}")',
            '',
            'if __name__ == "__main__":',
            '    executor = ProcessExecutor()',
            '    executor.execute()',
        ])

        return '\n'.join(code) 