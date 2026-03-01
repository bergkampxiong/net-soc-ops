# 渗透测试功能优化 PRD（产品需求文档）

**版本**：1.0  
**依据**：《渗透测试功能优化说明》  
**状态**：待评审

---

## 一、文档说明

### 1.1 目的

本 PRD 描述渗透测试功能优化需求，包括：**非静态测试时提供测试账号密码**、**统一渗透测试报告（含 LLM 中文化）**、**系统管理中的全局 OpenAI API Key 配置**。供开发排期与验收使用。

### 1.2 开发约束（必须遵守）

- **不修改现有其他功能代码**：本次仅新增渗透测试相关能力与系统管理中的全局 Key 配置；不改变现有业务逻辑、现有接口的请求/响应语义与现有前端页面的非渗透测试相关行为。若需在现有模块中增加逻辑（如流程设计器、作业执行），仅做**增量扩展**（如新增表单项、新增分支判断），不删除、不重写现有功能实现。
- **新增字段与表必须通过数据库初始化脚本完成**：
  - 所有**新增表**、**新增列**均须通过项目内的 **`int_all_db.py`** 完成初始化。
  - 在 `int_all_db.py` 中**仅允许**：新增本需求所需的 `init_*` / `ensure_*` 函数，并在 `init_databases()` 中**新增**对上述函数的调用。
  - **禁止**修改现有其它功能的数据库初始化逻辑：不得删减、不得修改现有 `init_*`、`ensure_*` 的实现与调用顺序，不得改动其它模块已使用的表结构初始化代码。
  - 新增列时优先使用 `ensure_*` 模式（检查列是否存在再 `ALTER TABLE ... ADD COLUMN`），与现有脚本风格保持一致。

---

## 二、需求背景与目标

### 2.1 背景

- 非静态（动态/灰盒）渗透测试时，提供测试账号密码可进行已认证扫描，提高漏洞发现率。
- 当前 Strix 输出为英文、多文件（总报告 + 各漏洞 .md），且下载接口仅支持 .html，无法直接获得人类友好、可交付的单一报告。
- 统一报告中文化需调用 LLM，与 Strix 扫描使用的 API Key 应隔离，故需在系统管理中提供「全局 OpenAI API Key」供 netops 其它功能使用。

### 2.2 目标

- 在流程设计器「渗透测试」节点支持可选填写**测试账号、测试密码**，并在执行时安全拼入 Strix instruction，不落库、不写日志。
- 支持**按需生成**并**下载/预览**一份**统一渗透测试报告**（总报告 + 全部漏洞合并，结构见 3.2），关键段落经 **LLM 中文化**；未配置全局 Key 或 LLM 失败时可降级为仅英文报告。
- 在**系统管理**中提供**全局 OpenAI API Key** 配置；渗透测试执行继续使用「渗透测试组件」内的 Strix API Token，与全局 Key 隔离。

---

## 三、功能范围与需求详情

### 3.1 渗透测试节点：测试账号与测试密码

| 项目 | 说明 |
|------|------|
| 位置 | 流程设计器 → 渗透测试节点配置面板（`pd-penetration-test-panel`） |
| 新增表单项 | 测试账号（可选）、测试密码（可选，Input.Password）；与「扫描模式」「自定义指令」同区域。 |
| UI 提示 | 在账号/密码区域增加说明或 Alert：「非静态测试时，可填写被测系统的测试账号与密码，以便进行已认证扫描，提高漏洞发现率；仅用于您已授权的测试环境。」 |
| 静态扫描时 | 当目标来源为「仅静态（代码审计）」或 `staticOnly === true` 时，账号/密码表单项禁用或折叠，并提示「仅静态扫描不需要系统账号密码」。 |
| 后端 | 作业执行（如 `job.py` 处理渗透测试节点）时，若节点数据带 `testUsername`/`testPassword`，将其格式化为一段说明拼接到 `instruction` **前部**再传给 Strix；密码仅内存使用，不落库、不写日志。 |
| 数据模型 | 流程定义中节点 `data` 增加可选字段 `testUsername`、`testPassword`（前端提交时与现有字段一起保存）；**不需要**在数据库新增表或列，仅流程 JSON 内扩展。 |

### 3.2 统一渗透测试报告

**报告结构**（输出为单一 .md，可选转 HTML）：封面/元信息 → 执行摘要（中文）→ 测试范围与方法论（中文）→ 漏洞发现总览（表格）→ 漏洞详情（逐条，中文）→ 技术分析总结（中文）→ 修复与改进建议（中文）→ 附录（可选）。详见《渗透测试功能优化说明》3.2。

**功能边界**：单次扫描对应一份统一报告；支持「按需生成」和/或「扫描完成后异步生成」；支持下载与在线预览。多扫描合并、PDF 导出、报告模板可配置、多语言切换不在本版。

**数据来源**：从 `StrixScanTask.report_path` 解析目录（含子目录），读取 `penetration_test_report.md` 与 `vulnerabilities/*.md`（及可选 `vulnerabilities.csv`），按《渗透测试功能优化说明》3.3 路径与顺序约定解析。

**后端流程**：解析 report_path → 读取总报告与漏洞列表 → 拼接英文草稿 →（可选）使用**全局 OpenAI API Key** 调用 LLM 对执行摘要、方法论、技术分析、修复建议及每条漏洞的描述/影响/复现/修复等段落做中文翻译与润色 → 输出 `unified_penetration_test_report.md` 及可选 HTML → 落盘并记录「已生成」状态。

**接口**：

| 接口 | 方法 | 说明 |
|------|------|------|
| 生成统一报告 | `POST /api/config-module/strix/scans/{task_id}/unified-report` | 触发生成；返回 202/200，body 可含 `unified_report_path` 或 `ready`。异步时需轮询或回调。 |
| 获取统一报告（下载） | `GET /api/config-module/strix/scans/{task_id}/unified-report` | 已生成则返回文件流（.md 或 .html），设置 Content-Type、Content-Disposition；未生成可 404/409。 |
| 获取统一报告（预览） | `GET /api/config-module/strix/scans/{task_id}/unified-report?format=html` 或单独 path | 已生成 HTML 则返回 HTML；无则 404。 |

**LLM 失败与降级**：未配置全局 Key 或超时/限流时，可降级为仅英文拼接或在报告中注明「未进行中文润色」，或返回错误提示配置 Key 后重试；不阻塞报告下载。

**数据库**：若需记录「统一报告已生成」及路径，须通过 **`int_all_db.py`** 扩展：在 `strix_scan_tasks` 上**新增列**（如 `unified_report_path`、`unified_report_generated_at`），通过新增 `ensure_strix_scan_task_unified_report(engine)` 并在 `init_strix_tables()` 末尾或 `init_databases()` 中在 `init_strix_tables(engine)` 之后调用；**不修改**现有 `init_strix_tables` 内已有表创建逻辑。

### 3.3 系统管理：全局 OpenAI API Key

| 项目 | 说明 |
|------|------|
| 入口 | 系统管理（仅管理员可见的菜单下） |
| 能力 | 提供「OpenAI API Key」或「全局 LLM API Key」配置项，支持保存与读取；敏感展示脱敏（如 ********）。 |
| 用途 | 供 netops 全局功能使用，本版仅用于统一渗透测试报告的 LLM 中文化与润色；与渗透测试组件（Strix）的 API Token 完全隔离。 |
| 后端 | 需可安全读取（如环境变量或加密/脱敏存储）；仅后端使用，不暴露到前端。 |
| 数据库 | 若采用表存储，须**新增表**（如 `system_global_config`，字段如 `config_key`、`config_value`、`updated_at`），通过 **`int_all_db.py`** 完成初始化：新增 `init_system_global_config_tables(engine)`，在 `init_databases()` 中**追加**一次调用；**不修改**现有任何其它 `init_*` 或 `ensure_*` 的实现与调用。 |

### 3.4 前端行为汇总

- **渗透测试报告列表/详情页**：每条扫描展示「生成统一报告」（未生成时）或「下载统一报告」「预览」（已生成时）；未配置全局 Key 时提示「请先在系统管理中配置 OpenAI API Key 以启用报告中文化」；LLM 失败时展示降级说明或重试入口。
- **现有「下载报告」**：可优先引导「下载统一报告」；若统一报告未生成，可回退为下载原始报告（现有 .html 逻辑或扩展支持返回 `penetration_test_report.md`）。

---

## 四、数据库变更要求（仅通过 int_all_db.py）

### 4.1 原则

- 所有本需求涉及的**新增表**、**新增列**均通过 **`int_all_db.py`** 初始化。
- 在 `int_all_db.py` 中**仅允许**：
  - 新增本需求所需的 `init_*`、`ensure_*` 函数；
  - 在 `init_databases()` 中**新增**对这些函数的调用（或在本需求相关的现有 init 末尾调用 ensure）。
- **禁止**：修改现有其它功能的数据库初始化逻辑（不删减、不修改现有 init_* / ensure_* 的实现与调用顺序）。

### 4.2 建议变更清单

| 变更类型 | 说明 | 在 int_all_db.py 中的做法 |
|----------|------|----------------------------|
| 新表：全局配置 | 若采用表存全局 OpenAI Key，如表名 `system_global_config`，字段 `config_key`、`config_value`、`updated_at` 等 | 新增 `init_system_global_config_tables(engine)`，内部 `__table__.create(engine, checkfirst=True)`；在 `init_databases()` 末尾新增一行调用。 |
| 新列：统一报告状态 | 若在 `strix_scan_tasks` 上记录统一报告路径或生成时间，如 `unified_report_path`、`unified_report_generated_at` | 新增 `ensure_strix_scan_task_unified_report(engine)`，内部检查列是否存在后 `ALTER TABLE strix_scan_tasks ADD COLUMN ...`；在 `init_strix_tables(engine)` 之后调用（或在 `init_strix_tables` 末尾调用 ensure），**不修改**现有 `StrixScanTask.__table__.create` 等逻辑。 |

具体表名、列名以最终设计与模型定义为准；实现时须符合 4.1 原则。

---

## 五、非功能需求

- **性能**：统一报告生成可能耗时较长（尤其启用 LLM），建议异步生成 + 轮询或完成通知；或同步但设置合理超时与前端 loading。
- **安全**：测试密码仅内存拼接、不落库不写日志；统一报告可能含敏感内容，下载/预览与现有权限一致；全局 API Key 仅后端使用、不暴露前端。
- **兼容**：现有 `GET /config-module/strix/scans/{task_id}/report` 保留不变；统一报告通过新接口暴露。

---

## 六、验收标准

### 6.1 测试账号与密码

- 渗透测试节点配置中可见可选「测试账号」「测试密码」及约定提示；静态扫描时该区域禁用或折叠并有说明。
- 填写后执行作业，Strix 能收到包含账号密码说明的 instruction；密码未出现在数据库与日志中。

### 6.2 统一报告

- 对已完成的 Strix 扫描（含 report_path 及 penetration_test_report.md、vulnerabilities/），可触发生成并下载符合 3.2 结构的单一文档（.md 或 .html）。
- 在已配置全局 OpenAI Key 且 LLM 成功时，执行摘要、方法论、技术分析、修复建议及漏洞详情的自然语段为中文；层次清晰，代码块与表格保留。
- 报告列表/详情页具备「生成统一报告」「下载统一报告」「预览」入口；未配置全局 Key 或 LLM 失败时有明确提示或降级，不阻塞报告下载。

### 6.3 系统管理全局 Key

- 系统管理页可配置并保存全局 OpenAI API Key；展示脱敏；统一报告生成时仅使用该 Key，渗透测试执行仍使用渗透测试组件的 Token。

### 6.4 开发约束

- 现有其他功能行为与接口保持不变；数据库仅通过 `int_all_db.py` 新增本需求所需的表/列初始化，且不修改现有其它功能的初始化逻辑。

---

## 七、参考文档

- 《渗透测试功能优化说明》（含统一报告结构、数据来源、接口、API Key 策略、非功能与验收要点）

---

*PRD 版本 1.0 | 依据《渗透测试功能优化说明》编写*
