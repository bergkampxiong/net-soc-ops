# Strix 集成 — 开发计划 PRD

> 依据《Strix_集成方案》整理的可执行开发计划，按阶段拆分任务与验收标准，供排期与落地使用。

---

## 一、文档说明与实施顺序

### 1.1 阶段总览

| 阶段 | 内容 | 优先级 | 依赖 |
|------|------|--------|------|
| **阶段 1** | 后端：Strix 扫描任务表与 API（创建/列表/详情/报告/取消） | P0 | Strix 子模块已就绪、Docker 可用 |
| **阶段 2** | 后端：OpenAPI（LLM）配置存储与接口；前端：渗透测试组件页（配置 + 任务列表 + 报告查看） | P0 | 阶段 1 |
| **阶段 3** | 流程校验放宽 + 作业执行器对渗透测试节点的处理（不生成代码、调 Strix API） | P0 | 阶段 1 |
| **阶段 4** | 流程设计器：扫描目标节点 + 渗透测试节点及配置面板 | P1 | 阶段 2、3 |
| **阶段 5** | 渗透测试报告：任务作业管理下独立列表/详情页 + 与作业执行关联落库 | P1 | 阶段 1、3 |
| **阶段 6** | 作业详情页联动「查看渗透测试报告」入口 | P2 | 阶段 5 |

### 1.2 核心约定（来自集成方案）

- **渗透测试节点不参与代码生成**：仅设备连接、配置备份、配置下发参与 `CodeGenerator.generate_code()`；渗透测试由作业执行器解析流程后调用后端 Strix API。
- **流程校验放宽**：若存在 `penetrationTest` 节点，则不强制要求设备连接与配置下发/备份；须有开始 + 结束。
- **渗透测试报告独立**：作业详情只展示脚本执行日志与状态；完整漏洞/报告在「渗透测试报告」模块中展示，作业详情仅提供跳转入口。

---

## 二、阶段 1：后端 Strix 扫描任务与 API

### 2.1 目标

实现扫描任务的创建、列表、详情、报告获取与取消；执行时通过 CLI 子进程调用 Strix，结果落库并可供前端拉取。

### 2.2 数据模型

| 表名 | 用途 | 主要字段（示例） |
|------|------|------------------|
| `strix_scan_tasks` | 单次扫描任务 | id, target_type, target_value(JSON/文本), instruction, scan_mode, status(pending/running/success/failed/cancelled), run_name, job_execution_id(可选), created_by, created_at, finished_at, summary(JSON: 漏洞数等), report_path |

- `job_execution_id`：作业执行器调用创建扫描时写入，用于渗透测试报告列表按执行关联。

### 2.3 后端接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/config-module/strix/scans` 或 `/api/security/strix/scans` | 创建扫描，body: target_type, target_value, instruction, scan_mode 等；返回任务 id、run_name。 |
| GET | `.../scans` | 列表，分页 + 按 status、job_execution_id、时间范围筛选。 |
| GET | `.../scans/{id}` | 任务详情与状态。 |
| GET | `.../scans/{id}/report` | 报告内容或文件流（从 strix_runs 或落库路径读取）。 |
| POST | `.../scans/{id}/cancel` | 取消运行中任务（子进程终止）。 |

### 2.4 执行逻辑

- 创建工作目录：如 `data/strix_workspace/{run_name}`，避免并发冲突。
- 调用方式：在 `netops-backend/strix` 下激活 Strix 的 venv，执行 `strix -n --target <目标> [--scan-mode ...] [--instruction ...]`；可选异步（Celery/后台线程）或同步（接口内等待）。
- 结果：将 run_name、report_path、status、summary 写入 `strix_scan_tasks`；报告文件从 Strix 输出目录读取并可通过 `/scans/{id}/report` 返回。

### 2.5 验收标准

- [ ] 可通过 API 创建扫描任务，任务状态正确更新（pending → running → success/failed）。
- [ ] 列表与详情接口返回正确；支持按 `job_execution_id` 筛选。
- [ ] 报告接口可返回或下载 Strix 生成的报告内容。
- [ ] 取消接口能终止正在运行的任务。

---

## 三、阶段 2：OpenAPI 配置 + 渗透测试组件页

### 3.1 后端：OpenAPI（LLM）配置

| 项 | 说明 |
|----|------|
| 存储 | 配置表或 key-value 表（如 `strix_config`），存 STRIX_LLM、LLM_API_KEY、LLM_API_BASE、PERPLEXITY_API_KEY、STRIX_REASONING_EFFORT 等；API Key 加密或权限控制。 |
| 接口 | GET/PUT `.../strix/config`；GET 时敏感字段脱敏展示。 |
| 执行时 | 创建/执行扫描时从该配置注入环境变量，不写死在代码中。 |

### 3.2 前端：渗透测试组件入口

| 项 | 说明 |
|----|------|
| 菜单位置 | 自动化 RPA → 原子功能组件库 → **渗透测试**（与设备连接、配置管理等并列）。 |
| 路由 | `/rpa/atomic-components/penetration-test`（或 `/rpa/atomic-components/strix`）。 |
| 页面职责 | ① **OpenAPI 配置**：表单编辑 LLM 模型、API Key、API Base 等，调用 GET/PUT strix/config；② **扫描任务**：创建任务（目标类型、URL/路径、指令、scan_mode）、任务列表（状态、时间、目标）、点击任务查看详情与报告（内嵌或下载）。 |

### 3.3 验收标准

- [ ] 渗透测试组件菜单可进入，OpenAPI 配置可保存并脱敏展示。
- [ ] 可创建扫描任务并看到列表；可查看任务详情与报告。
- [ ] 执行 Strix 时使用平台内配置的 LLM/API，不依赖仅环境变量。

---

## 四、阶段 3：流程校验放宽 + 作业执行器渗透测试节点

### 4.1 流程校验放宽

| 位置 | 修改内容 |
|------|----------|
| 前端 `validateProcess()` | 规则改为：必须包含开始 + 结束；且 **至少满足其一**：（a）至少一个设备连接 +（至少一个配置下发或配置备份），或（b）至少一个渗透测试节点。即纯「扫描目标 + 渗透测试」流程可保存。 |
| 后端 `CodeGenerator.validate()` | 与前端一致：若存在 `penetrationTest` 节点，则不强制要求 deviceConnect 与 configDeploy/configBackup；仍要求一个 start、一个 end。 |

### 4.2 作业执行器对渗透测试节点的处理

| 项 | 说明 |
|----|------|
| 代码生成 | `CodeGenerator.generate_code()` **不**处理 `penetrationTest`（及 `scanTarget`），仅处理 deviceConnect、configBackup、configDeploy，与现有一致。 |
| 执行顺序 | 若流程有设备/配置节点：先生成并执行 Python 脚本；若流程有渗透测试节点：在脚本执行后（或流程仅有渗透测试时直接）按 edges 拓扑顺序处理渗透测试节点。 |
| 单节点处理 | 解析 `penetrationTest` 的 data：targetSource（targetNode / inline）、targetNodeId、targetType、targets、instruction、scanMode 等；若 targetSource 为 targetNode，则从流程定义中取 targetNodeId 对应节点的 data.targets 等作为目标。 |
| 调用方式 | 对每个渗透测试节点：请求 POST `.../strix/scans` 传入目标与参数，轮询 GET `.../scans/{id}` 直至状态非 running（可配置超时）；将 `job_execution_id` 与返回的 scan 任务 id 关联落库，供渗透测试报告使用。 |
| 执行记录 | 同一 job_execution 下：脚本日志照常写入 execution.logs/result；渗透测试部分可在 result 中增加 strix_scan_ids 或由报告模块通过 job_execution_id 查询。 |

### 4.3 验收标准

- [ ] 仅含「开始 + 结束 + 扫描目标 + 渗透测试」的流程可保存并发布。
- [ ] 发布后作业出现在作业执行控制；执行时若无设备/配置节点则只执行渗透测试 API 调用；若有则先执行脚本再按顺序调用 Strix API。
- [ ] 执行后可在后端或报告模块通过 job_execution_id 查到本次执行触发的扫描任务。

---

## 五、阶段 4：流程设计器 — 扫描目标与渗透测试节点

### 5.1 扫描目标节点（scanTarget）

| 项 | 说明 |
|----|------|
| 节点类型 | `scanTarget`，左侧栏命名如「扫描目标」。 |
| 组件 | 节点组件 `PDScanTargetNode`；配置面板 `PDScanTargetPanel`。 |
| 配置项 | 目标类型（Web URL / Git 仓库 / 本地路径 / 域名或 IP）、目标值（支持多目标）、可选「使用本流程配置备份输出目录」。 |
| 持久化 | 节点 data：targetType、targets[]、useBackupOutput。 |

### 5.2 渗透测试节点（penetrationTest）

| 项 | 说明 |
|----|------|
| 节点类型 | `penetrationTest`，左侧栏「渗透测试」。 |
| 组件 | `PDPenetrationTestNode`；配置面板 `PDPenetrationTestPanel`。 |
| 目标来源 | 单选「从目标节点获取」或「本节点内填写」。若选「从目标节点获取」，下拉选择当前流程中的某个「扫描目标」节点（按 id 或 label）；若选「本节点内填写」，则展示目标类型 + 目标值（同扫描目标节点）。 |
| 扫描配置 | scan_mode（quick/standard/deep）、instruction、instruction_file、可选扫描预设等。 |
| 持久化 | targetSource、targetNodeId、targetType、targets[]、instruction、scanMode、presetId 等。 |

### 5.3 设计器联动

- `onNodeClick` 中增加对 `scanTarget`、`penetrationTest` 的分支，打开对应配置面板。
- 保存流程时各节点 data 正确持久化；校验规则已按阶段 3 放宽。

### 5.4 验收标准

- [ ] 可从左侧拖入「扫描目标」「渗透测试」节点并连线。
- [ ] 扫描目标节点可配置目标类型与多目标；渗透测试节点可选择「从目标节点获取」并选择扫描目标节点，或本节点内填写目标。
- [ ] 渗透测试节点可配置 scan_mode、instruction 等；保存后再次打开流程，配置正确回显。
- [ ] 含上述节点的流程可保存、发布，并在作业执行控制中执行（执行逻辑由阶段 3 保证）。

---

## 六、阶段 5：渗透测试报告（任务作业管理下）

### 6.1 菜单位置与路由

| 项 | 说明 |
|----|------|
| 菜单位置 | **任务作业管理** 下新增子菜单：**渗透测试报告**（与「作业执行控制」「作业监控与报告」并列）。 |
| 路由 | `/rpa/task-job-management/penetration-reports`；列表与详情可分别为 `.../penetration-reports`、`.../penetration-reports/:id`。 |

### 6.2 列表页

| 项 | 说明 |
|----|------|
| 数据维度 | 按「扫描」展示：关联 job_execution_id、作业名称、扫描目标、扫描时间、状态、严重程度汇总（高/中/低数量，若后端有解析）等。 |
| 筛选 | 时间范围、作业（或 job_execution_id）、目标、状态。 |
| 数据来源 | 阶段 1 的 strix_scan_tasks 表（含 job_execution_id）；列表接口如 GET `.../strix/reports` 或 GET `.../strix/scans` 支持按 job_execution_id、时间等筛选。 |

### 6.3 详情页

| 项 | 说明 |
|----|------|
| 内容 | 单次扫描：漏洞列表（名称、严重程度、状态、描述）、可选严重程度分布图、扫描时长、目标信息。 |
| 报告下载 | 提供「下载报告」按钮，对接阶段 1 的 GET `.../scans/{id}/report`（Strix 原生 HTML/PDF 等）。 |
| 数据来源 | 详情接口 GET `.../scans/{id}` 扩展返回漏洞列表（若后端有解析）；或前端从 report 接口获取内容后解析展示。 |

### 6.4 后端补充

- 列表接口需支持按 `job_execution_id` 筛选，并返回作业名称（可联表 jobs + job_executions）。
- 若需严重程度汇总，可在任务完成时解析 Strix 输出写入 `strix_scan_tasks.summary` 或单独结果表。

### 6.5 验收标准

- [ ] 任务作业管理下可见「渗透测试报告」入口，列表展示扫描记录及关联作业执行/作业名。
- [ ] 支持按时间、作业、状态筛选；点击进入详情可查看漏洞列表与报告下载。
- [ ] 由作业执行触发的扫描在列表中能通过 job_execution_id 关联展示。

---

## 七、阶段 6：作业详情联动「查看渗透测试报告」

### 7.1 需求

在作业详情的「执行历史」表格中，当某条执行记录包含渗透测试节点时，提供入口跳转到渗透测试报告，不在作业详情页内嵌完整漏洞表。

### 7.2 实现要点

| 项 | 说明 |
|----|------|
| 判断 | 若该 job 关联的流程定义中存在 `penetrationTest` 节点，则在该执行记录行显示「查看渗透测试报告」按钮或链接。 |
| 跳转 | 跳转到渗透测试报告列表页并带参数过滤 `job_execution_id = 当前执行 ID`，或直接打开该次执行对应的第一条扫描报告详情（若一次执行对应多次扫描，以列表过滤为佳）。 |

### 7.3 验收标准

- [ ] 当作业关联流程含渗透测试节点时，执行历史中该次执行有「查看渗透测试报告」入口。
- [ ] 点击后进入渗透测试报告列表（仅该 job_execution_id）或对应报告详情，不要求在作业详情页展示漏洞列表。

---

## 八、依赖与接口汇总

### 8.1 后端接口清单（Strix 相关）

| 方法 | 路径 | 阶段 |
|------|------|------|
| POST | `/api/config-module/strix/scans` 或 `/api/security/strix/scans` | 1 |
| GET | `.../strix/scans`（列表、筛选） | 1 |
| GET | `.../strix/scans/{id}` | 1 |
| GET | `.../strix/scans/{id}/report` | 1 |
| POST | `.../strix/scans/{id}/cancel` | 1 |
| GET / PUT | `.../strix/config` | 2 |

### 8.2 前端路由与菜单

| 菜单路径 | 路由 | 阶段 |
|----------|------|------|
| 自动化 RPA → 原子功能组件库 → 渗透测试 | `/rpa/atomic-components/penetration-test` | 2 |
| 任务作业管理 → 渗透测试报告 | `/rpa/task-job-management/penetration-reports` | 5 |

### 8.3 依赖与风险（简述）

- **Docker**：Strix 运行依赖 Docker，部署环境需可用。
- **Strix 版本**：以子模块锁定版本为准，升级时需回归 CLI 参数与输出格式。
- **长任务与超时**：扫描可配置超时；建议执行器轮询 Strix 状态时设置合理超时与取消能力。
- **敏感数据**：报告与配置中的 API Key 需权限控制与脱敏，不对外暴露工作目录。

---

## 九、参考文档

- [Strix_集成方案](./Strix_集成方案.md)
- [INSTALL.md 第八节 — Strix 工程](../INSTALL.md#八strix-工程可选)
