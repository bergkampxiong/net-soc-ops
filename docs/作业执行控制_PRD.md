# 作业执行控制 - 产品需求文档（PRD）

**文档版本**：1.0  
**关联设计**：`docs/作业执行控制_功能重构设计.md`  
**涉及代码**：作业执行控制前后端、流程管理发布、流程代码生成与配置管理模块

---

## 1. 背景与目标

### 1.1 背景

- **流程管理**（`/rpa/process-orchestration/process-management`）支持将流程发布为「已发布」状态，但发布后**不会**自动生成可执行作业。
- **作业执行控制**（任务作业管理 → 作业执行控制）当前支持**手动新建作业**（`JobForm`、`POST /api/jobs`），作业与流程定义无关联；执行作业时（`JobService.execute_job`、`app/services/job.py`）仅创建执行记录并更新 `last_run_at`，**不执行流程代码**；Celery 任务 `execute_job_task` 为占位 TODO。
- 配置备份类流程发布后，期望进入「作业执行控制」由管理员按需执行或设为定期执行，且执行结果（配置备份）能写入配置管理（`/config-module/management`）。当前流程代码生成（`app/process_designer/code_generator.py`）已实现调用 `POST /api/config-module/backups`，与配置管理页共用 `config_module_backups` 表，**数据链路已通**，需保证作业执行时真正跑流程代码并配置好执行环境。

### 1.2 产品目标

1. **作业仅来自流程发布**：作业执行控制不再提供「新建作业」；作业仅由「流程发布」自动创建。
2. **发布即一次作业**：发布后的流程自动生成一条「一次作业」，需管理员在作业执行控制中点击「执行」触发运行。
3. **可转为定期作业**：管理员可将「一次作业」改为「定期作业」并配置调度（cron/间隔等）。
4. **明确区分一次 / 定期**：列表与操作区分「一次作业」「定期作业」。
5. **执行即跑流程**：作业执行时根据关联流程定义生成并执行代码，配置备份等结果写入配置管理（已有接口与表）。

### 1.3 用户角色

| 角色 | 说明 |
|------|------|
| 管理员 | 在流程管理发布流程；在作业执行控制中执行作业、将一次作业转为定期、暂停/恢复/终止定期作业、查看执行历史。 |

---

## 2. 功能需求

### 2.1 流程发布时自动创建作业

| 需求 ID | 描述 | 验收标准 |
|---------|------|----------|
| F1.1 | 流程管理「发布」时，系统自动在 `jobs` 表创建一条作业，关联该流程定义 | 调用 `POST /api/process-definitions/{id}/publish` 成功后，存在一条 `process_definition_id = 该流程 id` 的作业 |
| F1.2 | 新创建的作业为「一次作业」（run_type=once），状态为 created | 作业 `run_type = 'once'`，`status = 'created'` |
| F1.3 | 同一流程多次发布（含「重新发布」）不重复创建作业，仅更新已有作业的 name 等可更新字段 | 按 `process_definition_id` 唯一；同一流程 ID 仅对应一条作业 |

**涉及代码**：  
- 后端：`netops-backend/app/api/process_management.py`（`publish_process_definition`）  
- 需在发布成功后插入/更新 `jobs` 表（见 3.1 数据模型）。

---

### 2.2 作业执行控制不提供「新建作业」

| 需求 ID | 描述 | 验收标准 |
|---------|------|----------|
| F2.1 | 作业执行控制列表页不展示「新建作业」按钮 | `JobExecution.tsx`、`JobList.tsx` 中移除或隐藏「新建作业」按钮 |
| F2.2 | 不提供从 UI 进入「新建作业」表单的入口 | 移除或隐藏跳转至 `/rpa/job-execution/jobs/new` 的入口；可选：保留路由但重定向到列表或 403 |
| F2.3 | 列表仅展示「由发布产生的」作业（即带 process_definition_id 的作业） | `GET /api/jobs` 默认或通过参数只返回 `process_definition_id IS NOT NULL` 的作业 |

**涉及代码**：  
- 前端：`netops-frontend/src/pages/rpa/JobExecution.tsx`、`netops-frontend/src/pages/rpa/job-execution/JobList.tsx`（移除 `PlusOutlined` 新建按钮及 `navigate('/rpa/job-execution/jobs/new')`）  
- 后端：`netops-backend/app/api/job.py`（`get_jobs`）、`app/services/job.py`（`get_jobs` 增加过滤）。

---

### 2.3 区分「一次作业」与「定期作业」

| 需求 ID | 描述 | 验收标准 |
|---------|------|----------|
| F3.1 | 列表展示「运行类型」：一次 / 定期 | 表格列或 Tag 显示 run_type（once → 一次作业，scheduled → 定期作业） |
| F3.2 | 支持按运行类型筛选 | `GET /api/jobs` 支持 query 参数 `run_type`（once / scheduled）；前端筛选项包含「全部 / 一次作业 / 定期作业」 |
| F3.3 | 详情页展示运行类型、关联流程、调度配置（定期时） | JobDetail 展示 run_type、process_definition_id（或流程名称）、schedule_config、next_run_at |

**涉及代码**：  
- 前端：`JobExecution.tsx`、`JobList.tsx`、`JobDetail.tsx`、`job-execution/types.ts`（增加 `run_type`、`process_definition_id` 等类型）  
- 后端：`app/api/job.py`（get_jobs 增加 `run_type` 参数）、`JobService.get_jobs` 过滤与返回字段。

---

### 2.4 管理员执行「一次作业」

| 需求 ID | 描述 | 验收标准 |
|---------|------|----------|
| F4.1 | 管理员在列表或详情页点击「执行」，触发该作业运行 | 调用 `POST /api/jobs/{id}/execute`；后端根据 `job.process_definition_id` 获取流程定义并执行（见 2.7） |
| F4.2 | 执行过程异步或同步均可；执行记录写入 job_executions，状态与日志可查 | 有对应 JobExecution 记录；status 经历 running → completed/failed；logs/error_message 可展示 |

**涉及代码**：  
- 前端：现有「执行」按钮已调 `POST /api/jobs/{id}/execute`，保持不变或增强 loading/结果提示  
- 后端：`app/api/job.py`（execute_job）、`app/services/job.py`（execute_job）需改为「拉取流程 → 生成代码 → 执行并更新 JobExecution」。

---

### 2.5 管理员将「一次作业」转为「定期作业」

| 需求 ID | 描述 | 验收标准 |
|---------|------|----------|
| F5.1 | 一次作业在列表或详情页提供「转为定期」操作 | 仅当 run_type=once 时显示「转为定期」按钮或链接 |
| F5.2 | 转为定期时弹出或跳转至调度配置表单（cron 表达式、间隔、时区等） | 可复用现有 schedule_config 结构（ScheduleConfig）；提交后 `run_type` 更新为 scheduled，并写入 schedule_config |
| F5.3 | 后端支持通过 `PUT /api/jobs/{id}` 更新 run_type 与 schedule_config | JobUpdate schema 及 JobService.update_job 支持 run_type、schedule_config；仅当 run_type=scheduled 时校验 schedule_config 必填或有效 |

**涉及代码**：  
- 前端：`JobList.tsx`、`JobDetail.tsx` 增加「转为定期」；可选新组件或复用 `JobForm` 仅调度部分；`types.ts` 增加 run_type、process_definition_id  
- 后端：`app/schemas/job.py`（JobBase/JobUpdate 增加 run_type）、`app/models/job.py`（run_type 列）、`JobService.update_job`。

---

### 2.6 定期作业的暂停 / 恢复 / 终止与编辑调度

| 需求 ID | 描述 | 验收标准 |
|---------|------|----------|
| F6.1 | 定期作业支持暂停、恢复、终止（与现有逻辑一致） | 继续使用 `POST /api/jobs/{id}/pause`、`resume`、`terminate` |
| F6.2 | 定期作业支持「编辑」调度配置（不改变 run_type） | 编辑仅更新 schedule_config、next_run_at 等；不提供删除作业（或仅允许管理员软删，按产品策略） |

**涉及代码**：  
- 前端：`JobDetail.tsx` 已有暂停/恢复/终止、编辑；编辑跳转 `JobForm` 或仅开放调度配置表单  
- 后端：保持现有 pause/resume/terminate；`PUT /api/jobs/{id}` 已支持更新，确保 schedule_config 可写。

---

### 2.7 作业执行时运行流程代码并写入配置管理

| 需求 ID | 描述 | 验收标准 |
|---------|------|----------|
| F7.1 | `POST /api/jobs/{id}/execute` 被调用时，若作业带 process_definition_id，则获取该流程定义（nodes/edges）并调用 CodeGenerator 生成 Python 代码 | 与 `process_management.generate_code` 使用同一 CodeGenerator（`app/process_designer/code_generator.py`）；生成逻辑一致 |
| F7.2 | 生成的代码在服务端或指定执行环境中执行；执行完成后更新对应 JobExecution 的 status、end_time、logs、error_message | 执行方式可为：子进程执行生成的脚本、或内嵌执行引擎；需能捕获 stdout/stderr 写入 logs，异常写入 error_message |
| F7.3 | 流程中含「配置备份」节点时，执行结果通过 `POST /api/config-module/backups` 写入；配置管理页（/config-module/management）能查到该备份 | 生成代码中已包含对 `CONFIG_MODULE_API_URL` + `/config-module/backups` 的调用；执行环境需能访问该 API；配置管理页使用 GET /config-module/backups，数据一致 |

**涉及代码**：  
- 后端：`app/services/job.py`（execute_job：查 process_definitions、调 CodeGenerator、执行脚本或引擎、更新 JobExecution）；`app/process_designer/code_generator.py`（已实现备份节点 → POST backups）  
- 配置模块：`netops-backend/routes/config_module.py`（POST /backups）、`netops-frontend/src/pages/ConfigModule/Management.tsx`（GET /backups 列表）；无需改配置管理功能，仅保证执行环境可访问 API。

---

## 3. 数据模型与接口

### 3.1 数据模型变更

**表：jobs（现有 + 新增字段）**

| 字段 | 类型 | 说明 | 变更 |
|------|------|------|------|
| id | Integer, PK | 主键 | 已有 |
| name | String(100) | 作业名称 | 已有 |
| description | Text | 描述 | 已有 |
| job_type | String(50) | 如 config_backup, network_config 等 | 已有 |
| status | String(20) | created / active / paused / terminated | 已有 |
| parameters | JSON | 执行参数 | 已有 |
| schedule_config | JSON | 调度配置；run_type=scheduled 时有效 | 已有 |
| **process_definition_id** | **String(36), NULL, index** | **关联 process_definitions.id** | **新增** |
| **run_type** | **String(20), default 'once'** | **once \| scheduled** | **新增** |
| created_at, updated_at, last_run_at, next_run_at, created_by, updated_by | 同现有 | - | 已有 |

- **约束**：作业执行控制仅展示 `process_definition_id IS NOT NULL` 的作业；同一 `process_definition_id` 仅允许一条作业（发布时 upsert 或先查后插）。
- **迁移**：新增两列可为 NULL/默认值，兼容已有数据；已有作业无 process_definition_id 视为「非发布来源」，列表过滤后不可见。

**涉及代码**：  
- `netops-backend/app/models/job.py`：增加 `process_definition_id`、`run_type` 列  
- `netops-backend/app/schemas/job.py`：JobBase/JobCreate/JobUpdate/JobResponse 增加 `process_definition_id`、`run_type`  
- 数据库：提供迁移脚本或 in `int_all_db.py` 的 `init_job_tables` 中通过 Alembic/raw SQL 增加列（若表已存在则 ALTER TABLE）。

### 3.2 流程发布创建/更新作业

- **时机**：`POST /api/process-definitions/{process_id}/publish` 成功更新 `process_definitions.status = 'published'` 之后。
- **逻辑**：  
  - 查询是否已存在 `process_definition_id = process_id` 的作业；  
  - 若存在：更新该作业的 name（从流程定义取）、updated_at 等；  
  - 若不存在：插入新作业，name、process_definition_id、job_type（如 `config_backup`）、run_type=`once`，status=`created`。
- **涉及代码**：`app/api/process_management.py` 中 `publish_process_definition` 内调用 Job 创建/更新（需注入 db 或使用同一 Session）。

### 3.3 接口规格

**GET /api/jobs**

| 参数 | 类型 | 说明 |
|------|------|------|
| skip, limit | int | 分页，已有 |
| name | string | 模糊筛选，已有 |
| job_type | string | 已有 |
| status | string | 已有 |
| **run_type** | **string** | **可选：once \| scheduled；不传则默认只返回 process_definition_id IS NOT NULL 的作业** |

- 响应：List[JobResponse]，JobResponse 中增加 `process_definition_id`、`run_type`（及可选 `process_definition_name` 由后端联表或二次查询）。

**POST /api/jobs**

- 行为变更：仅允许在「流程发布」流程中由后端内部调用，且必须带 `process_definition_id`；或对外保留但文档标明仅内部使用，前端不暴露创建表单。

**PUT /api/jobs/{job_id}**

- 请求体：支持 `run_type`、`schedule_config`；当 run_type=scheduled 时，schedule_config 必填且需包含 type（cron/interval 等）及对应字段。
- 涉及：`app/schemas/job.py`（JobUpdate）、`app/services/job.py`（update_job）。

**POST /api/jobs/{job_id}/execute**

- 行为：若 job.process_definition_id 为空，返回 400 或 404；否则按 2.7 执行流程并更新 JobExecution。

---

## 4. 前端规格

### 4.1 页面与路由

| 页面/路由 | 文件 | 变更要点 |
|-----------|------|----------|
| 作业执行控制（列表） | `src/pages/rpa/JobExecution.tsx`、`src/pages/rpa/job-execution/JobList.tsx` | 移除「新建作业」；增加运行类型列与 run_type 筛选；一次作业显示「执行」「转为定期」；定期作业显示「执行」「暂停」「恢复」「终止」「编辑」 |
| 作业详情 | `src/pages/rpa/job-execution/JobDetail.tsx` | 展示关联流程（名称 + 跳转链接）、run_type、schedule_config/next_run_at；一次作业突出「执行」「转为定期」；定期作业突出调度与暂停/恢复/终止 |
| 新建作业 | `src/pages/rpa/job-execution/JobForm.tsx`、路由 `job-execution/jobs/new` | 不再从列表进入；路由可保留用于「转为定期」时打开仅含调度配置的表单（或弹窗代替） |
| 编辑作业 | `job-execution/jobs/:id/edit` | 仅对定期作业开放；表单仅允许编辑调度相关字段（或整表单但 process_definition_id/run_type 只读） |

- 路由配置：`src/pages/rpa/index.tsx` 中 `job-execution/jobs/new` 可保留但无入口，或改为重定向到列表。

### 4.2 类型定义

- `src/pages/rpa/job-execution/types.ts`：  
  - 增加 `RunType = 'once' | 'scheduled'`。  
  - `JobListItem`、`JobFormData` 等增加 `process_definition_id?: string`、`run_type?: RunType`。  
  - `JobSearchParams` 增加 `run_type?: RunType`。

### 4.3 流程管理页

- 发布成功后，可 message 提示：「已发布，可在【作业执行控制】中执行或设为定期作业」。  
- 可选：在流程列表操作列增加「执行」链接，跳转到对应作业详情（需根据 process_definition_id 解析出 job_id，或后端提供「按 process_definition_id 查 job」接口）。

---

## 5. 非功能需求与约束

- **执行环境**：运行生成代码的进程需能访问 `CONFIG_MODULE_API_URL`（默认 `http://127.0.0.1:8000/api`），以便配置备份写入配置管理；若前后端分离部署，需配置网络与鉴权。
- **权限**：执行、转为定期、暂停/恢复/终止等可按现有权限体系限制为管理员（本 PRD 不规定具体权限模型）。
- **调度器**：本 PRD 不包含「定时触发定期作业」的调度器实现；转为定期后，next_run_at 与 schedule_config 的持久化与展示为必须，实际定时执行可后续迭代。

---

## 6. 实施检查清单

- [ ] **数据**：jobs 表增加 process_definition_id、run_type；迁移或 ALTER 脚本。
- [ ] **后端模型与 Schema**：Job 模型与 Pydantic 增加上述字段；JobService.get_jobs 支持 run_type 筛选并默认只返回带 process_definition_id 的作业。
- [ ] **发布创建作业**：publish_process_definition 内实现「按 process_definition_id 查/插/更新」作业逻辑。
- [ ] **执行作业**：execute_job 中根据 process_definition_id 取流程、CodeGenerator 生成代码、执行并更新 JobExecution（含 logs、error_message、status）。
- [ ] **PUT jobs**：支持 run_type、schedule_config 更新；一次→定期时校验 schedule_config。
- [ ] **前端**：移除新建作业入口；列表/详情展示 run_type、关联流程；增加「转为定期」与 run_type 筛选；类型定义与 API 传参对齐。
- [ ] **配置管理**：确认执行环境 CONFIG_MODULE_API_URL 可访问；无需改配置管理页与备份接口。
- [ ] **测试**：发布流程 → 作业列表出现对应一条作业；执行后 JobExecution 有记录且配置管理可见新备份；转为定期后 schedule_config 与 run_type 正确。
