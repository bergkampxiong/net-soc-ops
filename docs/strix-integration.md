# NetOps 中 Strix 工程集成说明

本文档列明在 NetOps 项目里与 Strix（渗透测试/安全扫描）相关的全部工作，便于排查问题与评估影响范围。

---

## 一、概述

- **Strix**：不在 git 中保存源码，由安装脚本 `scripts/install-strix.sh` 从 usestrix/strix 安装到 `netops-backend/strix/`（二进制在 `bin/strix`），执行任务时不使用 .venv。通过 CLI（`strix -n --target <目标>`）非交互执行。
- **安装约定**：Strix 安装在 `/app/net-soc-ops/netops-backend/strix`（或项目内同路径）；Docker 沙箱镜像拉取后存储由 Docker daemon 决定，若已执行 `install-netops.sh` 则数据目录为 `/app/docker`。
- **NetOps 侧**：提供 API、数据库、作业流程与前端页面，用于创建扫描任务、轮询状态、查看/生成报告、配置 LLM，并与流程设计器中的「渗透测试」节点联动。

---

## 二、后端（netops-backend）

### 2.1 路由与 API 挂载

- **文件**：`netops-backend/routes/strix_integration.py`
- **挂载**：在 `main.py` 中通过 `app.include_router(strix_router, prefix="/api/config-module")` 挂载，故所有 Strix API 前缀为 **`/api/config-module/strix`**。

### 2.2 Strix 相关 API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/config-module/strix/scans` | 创建扫描任务并异步执行，返回 `id`、`run_name`、`status` |
| GET | `/api/config-module/strix/scans` | 扫描任务列表，支持 `job_execution_id`、`status`、分页 |
| GET | `/api/config-module/strix/scans/{task_id}` | 单任务详情 |
| GET | `/api/config-module/strix/scans/{task_id}/report` | 原始报告内容（HTML 或 penetration_test_report.md 文本） |
| POST | `/api/config-module/strix/scans/{task_id}/unified-report` | 触发生成统一报告（读 Strix 输出，可选 LLM 中文化，落盘） |
| GET | `/api/config-module/strix/scans/{task_id}/unified-report` | 下载/预览统一报告（`.md` 或 `?format=html`） |
| POST | `/api/config-module/strix/scans/{task_id}/cancel` | 取消任务（标记取消，进程可能需超时退出） |
| DELETE | `/api/config-module/strix/scans/{task_id}` | 删除任务记录并删除磁盘报告目录（仅限 `data/strix_workspace` 下） |
| GET | `/api/config-module/strix/status` | 检查 Strix 是否已激活（源码存在且 CLI 可执行） |
| POST | `/api/config-module/strix/test-llm` | 用当前已保存配置发起最小 LLM 请求，校验 API Key |
| GET | `/api/config-module/strix/config` | 获取 Strix/LLM 配置（敏感字段脱敏） |
| PUT | `/api/config-module/strix/config` | 更新 Strix/LLM 配置（键值写入 `strix_config` 表，脱敏占位符不覆盖） |

### 2.3 数据库模型与表

- **文件**：`netops-backend/database/strix_models.py`
- **表**：
  - **`strix_scan_tasks`**：扫描任务元数据与状态（目标类型/值、指令、scan_mode、status、run_name、job_execution_id、report_path、unified_report_path、summary 等）。
  - **`strix_config`**：Strix/LLM 键值配置（如 STRIX_LLM、LLM_API_KEY、LLM_API_BASE、PERPLEXITY_API_KEY、STRIX_REASONING_EFFORT）。
- **初始化**：在 `int_all_db.py` 中通过 `import database.strix_models` 将上述表注册到 `database.base.Base`，并在建表逻辑中创建。

### 2.4 Strix CLI 调用与运行环境

- **文件**：`netops-backend/utils/strix_runner.py`
- **职责**：
  - **CLI 路径解析**：优先 `STRIX_CLI_PATH` 环境变量，其次 `netops-backend/strix/bin/strix`（由 `scripts/install-strix.sh` 安装，不使用 .venv），再次系统 PATH 的 `strix`。
  - **`check_strix_activation()`**：检查安装目录下 `bin/strix` 存在且可执行，或 `STRIX_CLI_PATH` 指向可执行文件；不依赖源码或 .venv。
  - **`get_strix_env_from_config(config_kv)`**：从 DB 配置键值构建 Strix 所需环境变量（STRIX_LLM、LLM_API_KEY、LLM_API_BASE 等）。
  - **`test_llm_config(config_kv)`**：用当前配置对 LLM 发起一次最小 chat 请求，校验可用性。
  - **`run_strix_sync(...)`**：在指定工作目录同步执行 `strix -n --non-interactive`，支持多目标、scan_mode、instruction；工作目录默认 `netops-backend/data/strix_workspace/<run_name>`，Strix 在 cwd 下生成 `strix_runs/`；返回 success、returncode、stdout、stderr、report_path 等。

### 2.5 统一报告构建

- **文件**：`netops-backend/utils/unified_report_builder.py`
- **职责**：读取 Strix 输出目录中的 `penetration_test_report.md` 及漏洞子目录，拼接为单一 Markdown，可选通过 LLM 做中文化；输出 `unified_penetration_test_report.md` 与 `unified_penetration_test_report.html`。
- **被调用**：`strix_integration.py` 中 `POST .../scans/{task_id}/unified-report` 使用 `build_unified_report` 生成并写回任务的 `unified_report_path`。

### 2.6 作业执行与渗透测试节点

- **文件**：`netops-backend/app/services/job.py`
- **逻辑**：当作业类型为渗透任务（流程中含渗透测试节点）时：
  - 使用 `CONFIG_MODULE_API_URL`（默认 `http://127.0.0.1:8000/api`）拼接 `POST /config-module/strix/scans` 创建扫描；
  - 请求体包含 target_type、targets、instruction、scan_mode、job_execution_id；目标来自流程中「扫描目标」节点或节点内联配置；
  - 创建后轮询 `GET /config-module/strix/scans/{scan_id}` 直至状态非 pending/running（最多约 1 小时，每 10 秒一次）；
  - 执行结果中记录 `strix_scan_ids` 与日志，便于前端从作业详情跳转渗透测试报告。

### 2.7 应用入口与 Strix 表注册

- **文件**：`netops-backend/main.py`
  - 引入 `routes.strix_integration.router` 为 `strix_router`，挂载到 `/api/config-module`；
  - 在初始化逻辑中 `import database.strix_models`，确保建表时包含 `strix_scan_tasks`、`strix_config`。

---

## 三、前端（netops-frontend）

### 3.1 页面与菜单

- **渗透测试组件**（配置 LLM/Strix）：`src/pages/rpa/atomic-components/penetration-test/index.tsx`  
  - 使用接口前缀 `STRIX_BASE = '/config-module/strix'`，调用 status、config、test-llm、config 更新等。
- **渗透测试报告**（报告列表与删除）：`src/pages/rpa/PenetrationReports.tsx`  
  - 同样使用 `STRIX_BASE`，调用 scans 列表、删除、统一报告生成/下载/预览等。
- **侧栏菜单**：`src/components/Layout.tsx` 中配置「渗透测试组件」「渗透测试报告」入口。

### 3.2 流程设计器与作业

- **渗透测试节点**：`src/components/process-designer/nodes/pd-penetration-test-node.tsx`（节点类型「渗透测试」）。
- **渗透测试节点配置面板**：`src/components/process-designer/panels/pd-penetration-test-panel.tsx`  
  - 目标仅允许从「扫描目标」节点获取；可配置 scan_mode（quick/standard/deep）、instruction、测试账号等。
- **扫描目标节点面板**：`src/components/process-designer/panels/pd-scan-target-panel.tsx`  
  - 支持 web_url / git_url / local_path / domain_ip 等目标类型，与渗透测试联动说明（黑盒/白盒、静态/动态）。
- **流程设计器主逻辑**：`src/components/process-designer/pd-flow-designer.tsx`  
  - 包含「渗透测试」节点类型、保存时处理渗透测试节点配置、校验流程时若存在渗透测试节点则不强制设备连接与配置下发/备份。
- **作业执行与展示**：
  - `src/pages/rpa/job-execution/JobForm.tsx`：作业类型选项含「渗透任务」；
  - `src/pages/rpa/job-execution/JobDetail.tsx`：作业详情中「查看渗透测试报告」及类型展示「渗透任务」；
  - `src/pages/rpa/JobExecution.tsx`、`src/pages/rpa/job-execution/JobList.tsx`：列表展示渗透任务类型。
- **请求超时**：`src/api/job.ts` 中针对渗透任务使用长超时，避免过早报错。

---

## 四、脚本与配置示例

### 4.1 脚本

- **`scripts/install-strix.sh`**  
  - 从 usestrix/strix 官方发布下载 Strix 二进制，安装到 `netops-backend/strix/bin/`（不使用 .venv）；支持指定安装目录为 `/app/net-soc-ops/netops-backend/strix`；拉取 Docker 沙箱镜像（镜像存储由 Docker daemon 配置决定，若已执行 install-netops 则在 /app/docker）。执行任务时不运行 .venv 环境。完成后可通过 `GET /api/config-module/strix/status` 自检。
- **`scripts/strix-container-ips.sh`**  
  - 列出当前运行的 Strix 沙箱容器（`docker ps --filter "name=strix-scan"`）名称与 IP，便于抓包排查。
- **`scripts/strix-config-amber-chatai.example.json`**  
  - Strix/LLM 配置示例（STRIX_LLM、STRIX_REASONING_EFFORT 等）。

### 4.2 目录与数据

- **Strix 安装目录**：`netops-backend/strix/`（由 install-strix.sh 填充，不含 git 中保存的源码）；二进制为 `strix/bin/strix`，执行任务不使用 .venv。
- **工作目录与报告**：`netops-backend/data/strix_workspace/` 下按任务创建子目录，Strix 在任务 cwd 下生成 `strix_runs/`；统一报告生成后路径写入 `strix_scan_tasks.unified_report_path`。
- **路径安全**：删除报告时通过 `_ensure_path_under_strix_workspace()` 限制仅可删除 `data/strix_workspace` 下的目录，避免误删系统路径。

---

## 五、依赖与调用链小结

1. **创建扫描**：前端/作业服务 → `POST /api/config-module/strix/scans` → 写入 `strix_scan_tasks` → 后台线程 `_run_scan_task` → `strix_runner.run_strix_sync` → 子进程执行 `strix -n ...`。
2. **配置与自检**：前端渗透测试组件 → `GET /api/config-module/strix/status`、`GET/PUT /config`、`POST /test-llm`；执行时 `get_strix_env_from_config` 从 `strix_config` 表注入环境变量。
3. **报告**：Strix 输出在 `data/strix_workspace/<run_name>/strix_runs/`；统一报告由 `unified_report_builder` 生成，通过 `POST/GET .../unified-report` 触发与下载。
4. **作业**：流程中渗透测试节点 → 作业执行时 `JobService` 解析节点、调用 `POST /config-module/strix/scans` 并轮询状态，结果与 `strix_scan_ids` 写入作业执行记录，前端从作业详情跳转渗透测试报告。

---

## 六、可能的问题与排查方向

- **Strix 未激活**：执行 `scripts/install-strix.sh` 或将 `STRIX_CLI_PATH` 指向 strix 二进制；调用 `GET /api/config-module/strix/status` 查看 source_present、cli_available、message。
- **扫描失败/超时**：查看任务 summary（stdout/stderr）、`data/strix_workspace` 下对应 run 的 `strix_runs` 输出；确认 LLM 配置与 `POST /test-llm` 是否通过。
- **作业渗透节点不执行**：确认 `CONFIG_MODULE_API_URL` 指向当前后端；流程中扫描目标节点已配置目标且渗透测试节点已关联目标。
- **统一报告生成失败**：确认任务 `report_path` 指向的目录内存在 Strix 生成的 `penetration_test_report.md`（或子目录结构符合 `unified_report_builder` 预期）；若使用 LLM 中文化，需配置可用 LLM。

以上为 NetOps 中与 Strix 工程相关的全部集成点，便于定位「重大问题」所涉模块与数据流。
