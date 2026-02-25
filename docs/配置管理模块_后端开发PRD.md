# 配置管理模块 — 后端开发 PRD

> 依据《配置管理模块 — 开发设计计划》细化，供后端开发落地使用。界面与接口说明统一使用中文。

---

## 一、文档说明与实施顺序

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| **阶段 1** | 配置管理（备份库）| P0 |
| **阶段 2** | 配置摘要 | P0 |
| **阶段 3** | 配置变更模板 | P1 |
| **阶段 4** | 合规 | P1 |
| **阶段 5** | 服务终止（可选）| P2 |

**说明**：作业（配置备份/下发/合规调度）不在本模块实现，由原子工作流与任务作业负责；本模块提供**配置备份写入接口**供流程中「配置备份」节点调用。

---

## 二、阶段 1：配置管理（备份库）

### 2.1 数据模型

**新建表：设备配置备份**（建议表名：`config_module_backups`，与现有 `rpa_config_files` 模板表区分）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Integer, PK | 是 | 主键 |
| device_id | String(64) | 是 | 设备标识（可与 CMDB 关联，或 host + 设备名） |
| device_name | String(128) | 否 | 设备显示名 |
| device_host | String(128) | 否 | 设备 IP/主机名，便于检索 |
| content | Text | 是 | 配置全文 |
| source | String(32) | 否 | 来源：`workflow` / `manual` / `api` |
| remark | String(500) | 否 | 备注 |
| version_no | Integer | 否 | 同设备下的版本号（可选，便于展示先后） |
| created_at | DateTime(TZ) | 是 | 备份时间 |
| created_by | String(64) | 否 | 创建人/系统标识 |

- **索引建议**：`(device_id, created_at)`、`device_host`、`created_at`，便于按设备、时间、IP 检索。
- **大文本**：若单条配置超 1MB，可考虑单独大表或对象存储，本表存 path 或 chunk 引用；首版可仅用 Text 存全文。

### 2.2 接口规范

**基础路径**：`/api/config-module`（或与现有统一前缀如 `/api/v1/config-module`）

| 方法 | 路径 | 说明 | 请求体/Query | 响应 |
|------|------|------|---------------------|------|
| POST | /backups | 写入一条备份（流程节点/API 调用）| body: device_id, device_name?, device_host?, content, source?, remark? | 201 + 备份对象（含 id, created_at） |
| GET | /backups | 分页列表 + 筛选 | query: device_id?, device_host?, keyword?, start_time?, end_time?, skip, limit | 200 + { items, total } |
| GET | /backups/{id} | 单条备份详情 | - | 200 + 备份对象（含 content） |
| GET | /backups/device/{device_id}/history | 单设备版本历史 | query: limit? | 200 + 按时间倒序的备份列表（可仅元数据不含 content） |
| GET | /backups/diff | 两版本 diff | query: id_a, id_b 或 version_a, version_b + device_id | 200 + { diff_text 或 segments } |
| DELETE | /backups/{id} | 删除一条备份（软删可选）| - | 204 |

- **写入接口**：流程执行引擎在「配置备份」节点执行完成后，调用 `POST /backups` 写入本模块；`source=workflow`，可选带 `remark`（如流程名称/执行 ID）。
- **检索**：`keyword` 可在 `device_name`、`device_host`、`remark` 或配置 `content` 中做 LIKE（注意大字段性能，可仅对元数据检索或限制 content 检索长度）。

### 2.3 与现有系统对接

- **流程设计器 / 执行引擎**：需在「配置备份」节点执行逻辑中，在拉取设备配置成功后调用本模块 `POST /api/config-module/backups`，传入 device_id、content、source=workflow 等。
- **CMDB**：device_id 可与 CMDB 资产 ID 或 host 一致，便于前端从 CMDB 选设备后筛选备份；首版可不强依赖 CMDB，仅存 device_id/device_host。

### 2.4 验收标准（阶段 1）

- [ ] 表 `config_module_backups` 创建并迁移成功。
- [ ] POST /backups 可写入并返回 id、created_at。
- [ ] GET /backups 支持按 device_id、时间范围、keyword 筛选与分页。
- [ ] GET /backups/device/{device_id}/history 返回该设备备份列表（时间倒序）。
- [ ] GET /backups/diff?id_a=1&id_b=2 返回两版本 diff（文本或结构化 diff）。
- [ ] 流程「配置备份」节点（或占位实现）可调用写入接口并落库。

---

## 三、阶段 2：配置摘要

### 3.1 统计需求

- 已纳入配置管理的**设备数**（有至少一条备份的 device_id 去重数）。
- **最近 24h / 7d** 备份成功数、失败数（若流程有上报失败，可单独表或字段；首版可仅统计成功写入数）。
- **最近变更次数**：可定义为最近 7d 备份条数或“设备数×备份次数”的简化统计。
- **合规通过率**：阶段 4 合规上线后，可在此返回通过率；阶段 2 可先返回占位或 0。

### 3.2 接口规范

| 方法 | 路径 | 说明 | 响应 |
|------|------|------|------|
| GET | /summary/stats | 配置摘要统计 | 200 + { device_count, backup_24h_success, backup_24h_fail, backup_7d_success, backup_7d_fail, change_count_7d?, compliance_pass_rate? } |
| GET | /summary/recent-backups | 最近备份列表（用于摘要页）| query: limit? default 10 | 200 + 备份列表（元数据，不含 content） |
| GET | /summary/recent-changes | 最近变更（可与 recent-backups 复用或按设备聚合）| query: limit? | 200 + 列表 |

### 3.3 验收标准（阶段 2）

- [ ] GET /summary/stats 返回设备数、24h/7d 备份数（成功/失败若有时）。
- [ ] GET /summary/recent-backups 返回最近 N 条备份记录，供摘要页展示。

---

## 四、阶段 3：配置变更模板

### 4.1 与现有配置模板的边界

- **现有**：`rpa_config_files` 存 jinja2 / textfsm / job 等**下发用模板**，供配置下发节点、配置生成组件使用。
- **本模块**：「配置变更模板」为可复用的**变更片段或模板**（如 ACL、NTP、SNMP 等），可与 `rpa_config_files` 复用表并增加**类型/用途**区分，或单独建「变更模板」表。

**推荐**：在现有 config 相关表增加 `usage` 或 `template_category`（如 `deploy` / `change_fragment`），本模块「配置变更模板」只展示/维护 usage=change_fragment 的模板；或新建表 `config_change_templates` 关联 device_type、tags。

### 4.2 接口规范（可选与现有 /config/files 合并）

若单独建表，建议：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /change-templates | 列表，筛选 device_type、tag |
| GET | /change-templates/{id} | 详情 |
| POST | /change-templates | 新增 |
| PUT | /change-templates/{id} | 更新 |
| DELETE | /change-templates/{id} | 删除 |

若复用现有 config 表，则沿用 `/api/config/files`，通过 type/usage 筛选「变更模板」类型即可；前端配置管理模块下「配置变更模板」页只请求该类型。

### 4.3 验收标准（阶段 3）

- [ ] 变更模板可 CRUD，并与设备类型/用途标签绑定。
- [ ] 流程或配置下发时可选用变更模板（与现有模板库打通方式二选一）。

---

## 五、阶段 4：合规

### 5.1 数据模型

- **合规策略表**（如 `config_compliance_policies`）：id, name, rule_type（must_contain / must_not_contain / regex / key_value）, rule_content, device_type?, created_at 等。
- **合规执行结果表**（如 `config_compliance_results`）：id, policy_id, backup_id 或 device_id + 某次备份 id, passed (bool), detail (JSON 或 Text), executed_at。
- **报告**：可为一次「对多设备/多策略」的执行生成一条报告记录，关联多条 result；或仅用 result 列表按 execution_batch_id 聚合展示。

### 5.2 接口规范

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/DELETE | /compliance/policies | 策略 CRUD |
| POST | /compliance/run | 对指定 backup_id 或 device_id（取最新备份）执行指定策略或全部策略，写入 result |
| GET | /compliance/results | 按设备、时间、策略、通过与否筛选结果列表 |
| GET | /compliance/reports | 按批次或时间查看报告聚合（可选） |

### 5.3 验收标准（阶段 4）

- [ ] 策略可 CRUD，支持至少一种规则类型（如 must_contain / regex）。
- [ ] 可对某条备份或某设备最新备份执行合规检查，结果落库并可查询。

---

## 六、阶段 5：服务终止（可选）

### 6.1 数据模型

- **EOS 信息表**（如 `config_eos_info`）：设备或型号维度的 EOS/EOL 日期、说明；可与 CMDB 设备/型号关联（device_id 或 model 等）。

### 6.2 接口规范

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/DELETE | /eos | EOS 信息 CRUD；列表支持「即将/已 EOS」筛选 |

### 6.3 验收标准（阶段 5）

- [ ] 可维护设备/型号的 EOS 信息，列表展示即将/已 EOS，供前端「服务终止」页使用。

---

## 七、通用要求

- **认证与权限**：所有接口需走现有认证中间件；是否按角色限制「配置管理模块」访问与写权限，与现有 RBAC 策略一致。
- **错误码与日志**：统一返回格式（如 { code, message, data }）；关键写操作打日志便于审计。
- **分页**：列表类接口统一 `skip` / `limit` 或 `page` / `page_size`，响应含 `total`。

---

## 八、与设计计划对照

| 设计计划章节 | 本 PRD 对应 |
|--------------|------------|
| 四、4.1 配置摘要 | 三、阶段 2 |
| 四、4.2 配置管理 | 二、阶段 1 |
| 四、4.3 配置变更模板 | 四、阶段 3 |
| 四、4.4 合规 | 五、阶段 4 |
| 四、4.6 服务终止 | 六、阶段 5 |
| 六、数据与后端建议 | 各阶段数据模型与接口 |

作业（4.5）不在本 PRD 实现；配置备份的**写入**由流程节点调用阶段 1 的 `POST /backups` 完成。
