# NetOps网络自动化平台

## 项目简介
NetOps是一个现代化的网络自动化平台，提供网络设备管理、配置管理、自动化运维等功能。支持LDAP认证和细粒度的权限管理。

## 功能特点

### 1. CMDB资产管理
- 数据查询：灵活的资产查询和过滤功能
- ADS自动发现：自动发现和更新网络设备
- 资产盘点：定期资产盘点和差异分析
- 模型管理：自定义资产模型和属性

### 2. 设备管理
- 设备分类：多维度设备分类管理
- 凭证管理：安全的设备访问凭证管理

### 3. 自动化RPA
#### 3.1 原子功能组件库
- 设备连接组件：统一的设备连接管理
- 配置管理组件：设备配置的备份和恢复
- 配置生成组件：基于模板的配置生成
- 数据采集组件：自动化数据采集
- 安全审计组件：配置合规性检查
- 告警与报告组件：异常检测和报告生成

#### 3.2 流程编排引擎
- 可视化流程设计器：拖拽式流程设计
- 流程管理：流程版本控制和发布管理

#### 3.3 任务作业管理
- 作业执行控制：手动和自动执行管理
- 作业调度管理：灵活的调度策略配置
- 任务队列管理：优先级和并发控制
- 作业监控与报告：实时监控和报告生成

#### 3.4 系统集成
- 监控系统集成：与主流监控系统对接
- 工单系统集成：与工单系统无缝集成

### 4. AIOPS智能运维
- 智能告警：基于机器学习的异常检测
- 根因分析：自动化的故障根因分析
- 预测性维护：设备健康状态预测

## 技术架构

### 前端技术栈
- React 18
- TypeScript
- Ant Design 5.x
- React Router 6
- Axios
- ECharts

### 后端技术栈
- Python 3.9+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- APScheduler

### 部署架构
- Docker容器化部署
- Nginx反向代理
- Gunicorn应用服务器
- Supervisor进程管理

## 快速开始

1. 克隆仓库
```bash
git clone https://github.com/your-username/netops.git
cd netops
```

2. 安装依赖
```bash
# 后端依赖
cd netops-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 前端依赖
cd ../netops-frontend
npm install
```

3. 配置环境
```bash
# 复制环境配置文件
cp .env.example .env
# 编辑.env文件，配置必要的环境变量
```

4. 启动服务
```bash
# 启动后端服务
cd netops-backend
python run.py

# 启动前端服务
cd ../netops-frontend
npm start
```

5. 访问系统
打开浏览器访问 http://localhost:3000

## 详细安装说明

请参考 [INSTALL.md](INSTALL.md) 获取详细的安装和配置说明。

## 开发指南

### 代码规范
- 前端遵循 [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- 后端遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- 使用ESLint和Pylint进行代码检查

### 提交规范
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 代码重构
- test: 测试用例
- chore: 构建过程或辅助工具的变动

### 分支管理
- master: 主分支，保持稳定
- develop: 开发分支
- feature/*: 功能分支
- hotfix/*: 紧急修复分支

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- 项目维护者：[Your Name]
- 邮箱：[your.email@example.com]
- 项目主页：[https://github.com/your-username/netops] 