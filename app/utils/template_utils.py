from jinja2 import Environment, FileSystemLoader, Template
import textfsm
from pathlib import Path
import os

class TemplateManager:
    def __init__(self):
        self.template_dir = Path("templates")
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def get_template(self, device_type: str, template_name: str) -> Template:
        """获取指定设备类型的Jinja2模板"""
        template_path = f"{device_type}/{template_name}.j2"
        return self.env.get_template(template_path)

    def get_textfsm_template(self, device_type: str, command: str) -> textfsm.TextFSM:
        """获取指定设备类型和命令的TextFSM模板"""
        template_path = self.template_dir / "textfsm" / f"{device_type}_{command}.textfsm"
        with open(template_path) as f:
            return textfsm.TextFSM(f)

    def render_config(self, device_type: str, template_name: str, variables: dict) -> str:
        """渲染配置模板"""
        template = self.get_template(device_type, template_name)
        return template.render(**variables)

    def parse_output(self, device_type: str, command: str, output: str) -> list:
        """解析命令输出"""
        template = self.get_textfsm_template(device_type, command)
        return template.ParseText(output) 