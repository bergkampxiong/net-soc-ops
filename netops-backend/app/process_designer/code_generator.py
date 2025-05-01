from typing import Dict, List, Any
from netmiko import ConnectHandler
from utils.connection_pool_manager import ConnectionPoolManager

class CodeGenerator:
    def __init__(self, process_definition: Dict[str, Any]):
        self.process_definition = process_definition
        self.nodes = process_definition.get('nodes', [])
        self.edges = process_definition.get('edges', [])
        self.connection_pool = ConnectionPoolManager()

    def validate(self) -> Dict[str, Any]:
        """验证流程定义的有效性"""
        errors = []
        
        # 检查必要的节点
        start_nodes = [node for node in self.nodes if node['type'] == 'pd_start']
        if len(start_nodes) != 1:
            errors.append('流程必须包含一个开始节点')
            
        end_nodes = [node for node in self.nodes if node['type'] == 'pd_end']
        if len(end_nodes) != 1:
            errors.append('流程必须包含一个结束节点')
            
        # 检查设备连接节点
        device_nodes = [node for node in self.nodes if node['type'] == 'pd_device_connect']
        if not device_nodes:
            errors.append('流程必须包含至少一个设备连接节点')
            
        # 检查配置下发节点
        config_nodes = [node for node in self.nodes if node['type'] == 'pd_config_deploy']
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
        device_nodes = [node for node in self.nodes if node['type'] == 'pd_device_connect']
        for node in device_nodes:
            device_config = node['data']
            code.extend([
                f'            # 连接设备 {device_config["name"]}',
                '            try:',
                f'                device = {device_config}',
                f'                connection = self.connection_pool.get_connection(device)',
                f'                connections["{device_config["name"]}"] = connection',
                '            except Exception as e:',
                f'                print(f"连接设备 {device_config["name"]} 失败: {{str(e)}}")',
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
        config_nodes = [node for node in self.nodes if node['type'] == 'pd_config_deploy']
        for node in config_nodes:
            config_data = node['data']
            code.extend([
                f'            # 下发配置到设备 {config_data["device"]}',
                '            try:',
                f'                connection = connections["{config_data["device"]}"]',
                f'                config = """{config_data["config"]}"""',
                '                output = connection.send_config_set(config.splitlines())',
                '                print(f"配置下发成功: {output}")',
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