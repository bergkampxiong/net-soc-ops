# 配置管理模块 — 前端开发 PRD

> 依据《配置管理模块 — 开发设计计划》与《配置管理模块 — 后端开发 PRD》细化，供前端开发落地使用。界面与菜单统一使用中文。

---

## 一、文档说明与实施顺序

| 阶段 | 内容 | 优先级 | 依赖后端 |
|------|------|--------|----------|
| **阶段 1** | 配置管理（备份库）页面 | P0 | 阶段 1 备份接口 |
| **阶段 2** | 配置摘要页 | P0 | 阶段 2 摘要接口 |
| **阶段 3** | 配置变更模板页 | P1 | 阶段 3 变更模板接口 |
| **阶段 4** | 合规页 | P1 | 阶段 4 合规接口 |
| **阶段 5** | 服务终止页（可选）| P2 | 阶段 5 EOS 接口 |

---

## 二、菜单与路由

### 2.1 菜单位置

- 在左侧导航中新增**一级菜单**：「配置管理模块」（与「自动化RPA」「CMDB」等并列）。
- **路由前缀**：`/config-module`。

### 2.2 子菜单与路由

| 菜单项（中文） | 路由 | 对应页面 |
|----------------|------|----------|
| 配置摘要 | `/config-module/summary` | ConfigModuleSummary |
| 配置管理 | `/config-module/management` | ConfigModuleManagement |
| 配置变更模板 | `/config-module/change-templates` | ConfigModuleChangeTemplates |
| 合规 | `/config-module/compliance` | ConfigModuleCompliance |
| 服务终止 | `/config-module/eos` | ConfigModuleEos（可选） |

### 2.3 前端实现要点

- **Layout.tsx**：在 `mainMenuItems` 中增加一项，key 为 `config-module`，icon 可选 `FileTextOutlined` 或 `FolderOpenOutlined`，children 为上述 5 个子项（key 与路由一致，如 `config-module/summary`）。
- **路由**：在 `App.tsx` 的 Layout 下增加 `<Route path="config-module/*" element={<ConfigModule />} />`，由 ConfigModule 内部用子路由渲染 summary / management / change-templates / compliance / eos。
- **选中态**：在 `getSelectedKey`、`getOpenKeys` 中增加对 `path.startsWith('/config-module')` 的处理，使「配置管理模块」及其子菜单高亮正确。

---

## 三、阶段 1：配置管理（备份库）页面

### 3.1 页面路由

- `/config-module/management`

### 3.2 功能描述

- **设备配置库**：列表展示备份记录，列包括：设备标识/名称、IP、备份时间、来源、备注、操作（查看、对比、删除）。
- **筛选**：按设备 ID、设备 IP/主机名、时间范围、关键词（备注或内容检索）筛选；支持分页。
- **单设备版本历史**：点击某设备或「版本历史」进入该设备的备份列表（按时间倒序），可查看每条备份的配置全文、对比两个版本（diff）、可选回滚（若后端支持）。
- **查看配置**：弹窗或侧栏展示配置全文，支持只读与复制；大文本可折叠或分页展示。
- **对比（diff）**：选择两个版本，调用 `GET /api/config-module/backups/diff?id_a=xx&id_b=yy`，展示 diff 结果（文本 diff 或并排/高亮差异）。

### 3.3 接口对接

| 前端操作 | 接口 |
|----------|------|
| 备份列表（含筛选、分页）| GET /api/config-module/backups |
| 单条详情（含 content）| GET /api/config-module/backups/{id} |
| 单设备版本历史 | GET /api/config-module/backups/device/{device_id}/history |
| 两版本 diff | GET /api/config-module/backups/diff?id_a=&id_b= |
| 删除 | DELETE /api/config-module/backups/{id} |

（写入备份由流程节点调用后端，本页无需「新建备份」按钮；若有手动上传入口可后续加。）

### 3.4 组件建议

- `ConfigModuleManagement.tsx`：主页面，含表格、筛选栏、分页。
- `BackupDetailDrawer.tsx` 或 `BackupDetailModal.tsx`：配置全文查看。
- `BackupDiffModal.tsx`：两版本 diff 展示（可复用现有 `ConfigVersionDiff` 思路）。
- 设备版本历史可用同一表格切换「全部」/「当前设备」数据源，或单独 Tab/子页。

### 3.5 验收标准

- [ ] 配置管理菜单可进入，列表展示备份记录，筛选与分页正常。
- [ ] 可查看单条配置全文。
- [ ] 可选择两版本进行 diff 展示。
- [ ] 单设备版本历史可查看；删除单条备份可用（需权限/二次确认）。

---

## 四、阶段 2：配置摘要页

### 4.1 页面路由

- `/config-module/summary`

### 4.2 功能描述

- **统计卡片**：已纳入配置管理的设备数、最近 24h 备份成功数、最近 7d 备份成功数（失败数若后端有则展示）、最近变更次数、合规通过率（合规上线后展示）。
- **简单图表**（可选）：如 7d 内每日备份数折线图、设备占比饼图等。
- **最近备份列表**：表格展示最近 N 条备份（设备、时间、来源），可点击跳转到「配置管理」对应设备或详情。

### 4.3 接口对接

| 前端操作 | 接口 |
|----------|------|
| 统计数字 | GET /api/config-module/summary/stats |
| 最近备份 | GET /api/config-module/summary/recent-backups?limit=10 |

### 4.4 组件建议

- `ConfigModuleSummary.tsx`：页面内嵌多个 `Card`（统计）+ 表格（最近备份）；图表可用现有图表库（如 ECharts/Recharts）按需加。

### 4.5 验收标准

- [ ] 配置摘要页展示设备数、24h/7d 备份数等统计。
- [ ] 最近备份列表可展示并可跳转到配置管理。

---

## 五、阶段 3：配置变更模板页

### 5.1 页面路由

- `/config-module/change-templates`

### 5.2 功能描述

- 列表展示「变更模板」（与现有配置管理组件的模板区分：此处为变更片段/用途标签）。
- 支持按设备类型、用途标签筛选；CRUD：新增、编辑、删除模板；可选与「配置管理」中某次备份做对比/预检查（若后端支持）。

### 5.3 接口对接

- 若后端单独提供：GET/POST/PUT/DELETE `/api/config-module/change-templates`。
- 若复用现有 config：GET `/api/config/files?template_type=xxx&usage=change_fragment` 等，写操作沿用现有 config 接口并带类型参数。

### 5.4 验收标准

- [ ] 变更模板列表可展示、筛选；可新增/编辑/删除模板，并与设备类型/标签绑定。

---

## 六、阶段 4：合规页

### 6.1 页面路由

- `/config-module/compliance`

### 6.2 功能描述

- **策略管理**：策略列表（名称、规则类型、适用设备类型等），支持新增、编辑、删除策略；规则类型至少支持「必须包含」「禁止包含」或正则等（与后端一致）。
- **执行与报告**：选择设备或设备组、选择策略（或全部），触发「执行合规检查」；结果列表按设备、时间、通过/不通过展示；可查看单次执行详情（哪些策略通过/不通过及原因）。

### 6.3 接口对接

- GET/POST/PUT/DELETE `/api/config-module/compliance/policies`
- POST `/api/config-module/compliance/run`（传入 device_id 或 backup_id、policy_ids）
- GET `/api/config-module/compliance/results`（筛选、分页）

### 6.4 验收标准

- [ ] 策略 CRUD 可用；可对指定设备/备份执行合规检查并查看结果列表与详情。

---

## 七、阶段 5：服务终止页（可选）

### 7.1 页面路由

- `/config-module/eos`

### 7.2 功能描述

- 列表展示设备/型号的 EOS/EOL 信息；支持「即将 EOS」「已 EOS」筛选；可新增、编辑、删除 EOS 记录；列表字段含设备/型号、EOS 日期、说明等。

### 7.3 接口对接

- GET/POST/PUT/DELETE `/api/config-module/eos`

### 7.4 验收标准

- [ ] EOS 信息可维护，列表可筛选并展示即将/已 EOS。

---

## 八、通用要求

- **语言**：界面与菜单全部中文。
- **风格**：与现有 NetOps 前端一致（Ant Design、布局、配色）。
- **权限**：若后端按角色控制配置管理模块，前端根据权限隐藏或禁用菜单/按钮。
- **错误与加载**：请求失败统一提示；列表与详情加载态（loading）需有。
- **与现有「配置管理组件」区分**：左侧「自动化RPA → 原子功能组件库 → 配置管理组件」仍为**下发用模板**（jinja2/textfsm/job）；「配置管理模块」为**设备配置备份与版本、合规、变更模板、服务终止**，二者菜单与路由不同，不混淆。

---

## 九、与设计计划对照

| 设计计划 | 本 PRD 对应 |
|----------|------------|
| 五、菜单与路由建议 | 二、菜单与路由 |
| 4.1 配置摘要 | 四、阶段 2 |
| 4.2 配置管理 | 三、阶段 1 |
| 4.3 配置变更模板 | 五、阶段 3 |
| 4.4 合规 | 六、阶段 4 |
| 4.6 服务终止 | 七、阶段 5 |

作业（4.5）不在本模块实现，前端不提供「作业」子菜单；配置备份的写入由流程节点调用后端完成。
