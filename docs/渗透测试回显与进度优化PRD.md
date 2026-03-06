# 渗透测试回显与进度优化 PRD

## 一、背景与问题

1. **API 读不到任务信息**：当前已取消运行中写入 `live_echo.txt`，仅靠 `progress.json` 提供进度；若正则匹配不稳定，前端/接口会拿不到 Vulnerabilities、Agents、Tools 等关键数据。
2. **Txt 写入方式与资源**：此前“按块实时 append”到 `live_echo.txt` 会导致磁盘 IO 高、文件重复内容多（TUI 多次刷新同一块界面），需要优化写入策略。
3. **progress 正则匹配不稳**：TUI 输出格式多样（如 `Agents 1  ·  Tools 34`、ANSI 码、冒号等），现有正则对 Vulnerabilities、Agents、Tools 后的数字有时匹配不到，导致 progress 接口返回 null。
4. **前端回显展示过多**：列表/详情中与“回显”相关的展示较多（如 summary 截断、多处 strix_stats），仅需保留**任务执行阶段的关键字段**展示即可。

---

## 二、优化目标

- 在**可控资源占用**下，保证运行中与结束后能可靠读到**关键进度信息**（模型、漏洞数、Agents、Tools）。
- Txt 回显文件**按固定时间点覆盖写入**（第 1/3/5 分钟 + 结束），不采用“一直回显写入”。
- progress.json **不按块实时写**；仅在每次覆盖写入 txt 后，根据当前内容解析一次并写 progress.json，前端按需读一次展示即可。
- 正则解析**以关键词为准**，匹配关键词后的数字，提高鲁棒性。
- 前端**仅保留任务执行阶段关键字段**的展示，不展示大段回显原文。

---

## 三、方案详情

### 3.1 Txt（live_echo.txt）写入方式优化（定时覆盖 + 结束写一次）

| 项目     | 说明 |
|----------|------|
| **触发时机** | **第 1 分钟、第 3 分钟、第 5 分钟**各写一次（覆盖），**任务结束时**再写一次；共最多 4 次写入。若任务在 1 分钟内结束，则仅在结束时写 1 次。 |
| **写入方式** | 每次均为**覆盖**：用当前已收集的 stdout+stderr 拼成内容，`open(live_echo_path, "w")` 后一次性写入，**不**在运行中按块 append。 |
| **路径**     | 继续使用 `run_dir/live_echo.txt`（如 `data/strix_workspace/job_{execution_id}_{idx}/live_echo.txt`）。 |
| **与 progress 的关系** | 每次覆盖写完 txt 后，用**同一段内容**在内存中解析出 model、vulnerabilities、agents、tools，**只写一次** progress.json。即 progress.json 也只在 1/3/5 分钟与结束时更新，不按块实时写。 |
| **效果**     | 写入次数固定且少，既能在运行中段看到回显与进度，又避免一直写导致的 IO 与重复内容；接口侧不频繁读 json，在 txt 复写后读一次展示即可。 |

**评价（采用该方案的理由）**：

- 比“仅结束写一次”更均衡：运行中 1/3/5 分钟能拿到阶段回显与进度，又不至于“每块都写”导致资源占用高。
- 比“一直回显写入”省资源：写入从“每块多次”降为固定 4 次（或更少），progress.json 同步降为同频更新，读侧按需读一次即可，避免 json 被频繁读写。

**实现要点**（`app/services/job.py`）：

- 在读取 stdout/stderr 的线程（或主流程）中维护**已运行时间**（或由定时器触发）：在**第 1 分钟、第 3 分钟、第 5 分钟**三个时间点各执行一次“用当前缓冲区拼出 full_stdout/full_stderr → 覆盖写 live_echo.txt → 解析 4 项 → 写 progress.json”。
- 任务结束（`proc.wait()` 返回或超时/异常收尾）时：拼好 `full_stdout`、`full_stderr`，写入 `task.summary`，再执行一次“覆盖写 live_echo.txt → 解析 4 项 → 写 progress.json”。
- 运行中**不再**在每读一块时就写 progress.json；仅在上述 1/3/5 分钟与结束时写。

---

### 3.2 progress.json 正则匹配优化（以关键词匹配数字）

| 项目     | 说明 |
|----------|------|
| **思路** | 不依赖“关键词与数字之间”的具体格式（空格、冒号、·、ANSI 等），**只认关键词 + 其后出现的数字**。 |
| **规则** | 先对整段文本做 ANSI 剥离（保持现有 `_strip_ansi`），再按下列方式提取： |
| **Model** | 保持现有或微调：匹配 `Model` 后的非空 token（如 `Model\s+(\S+)`），取到后对捕获组再做一次 ANSI 剥离与去 strix 展示用处理。 |
| **Vulnerabilities** | 以单词 `Vulnerabilities` 为锚点，匹配其**后**首次出现的连续数字：`Vulnerabilities.*?(\d+)`（非贪婪）。若 TUI 中同一关键词多次出现，可取**最后一次**（`Vulnerabilities.*(\d+)` 贪婪）表示当前进度。 |
| **Agents** | 同上：`Agents.*?(\d+)` 或取最后一次 `Agents.*(\d+)`。 |
| **Tools** | 同上：`Tools.*?(\d+)` 或取最后一次 `Tools.*(\d+)`。 |

**实现要点**（`utils/strix_runner.py` 与 `routes/strix_integration.py`）：

- 统一解析函数（如 `_parse_stdout_stats` 及路由层同类逻辑）：  
  - 先 `_strip_ansi(text)`。  
  - Model：沿用或微调现有正则。  
  - Vulnerabilities、Agents、Tools：使用“关键词 + .*(\d+)”取最后一次数字（或 .*?(\d+) 取第一次，按产品偏好定）。  
- 写入 `progress.json` 的字段不变：`model`、`vulnerabilities`、`agents`、`tools`；读取与返回格式不变。

---

### 3.3 前端：仅保留任务执行阶段关键字段展示

| 项目     | 说明 |
|----------|------|
| **列表页** | 不展示回显内容。列表接口可**不返回** `summary` 字段（或始终返回 `null`），仅保留任务元信息（id、目标、状态、创建时间、来源等）及可选 `strix_stats`（仅 4 项：model、vulnerabilities、agents、tools）用于表格内简要展示。 |
| **详情页** | **运行中/待执行**：仅展示基础信息（扫描 ID、目标、状态、来源、时间等） + **运行状态卡片**（模型、漏洞数、Agents、Tools 四项）；**不展示** summary 的 stdout/stderr 原文、不展示“运行回显”大段文本。 |
| **详情页** | **已结束**：可保留运行状态卡片展示 4 项（来自 `strix_stats` 或 progress 最后一次）；不展示大段回显原文；若需“查看完整日志”可保留入口（如按钮跳转 GET /echo 或下载），默认不展开。 |
| **接口** | GET /scans/{id}/echo 可保留，供“按需查看完整回显”；前端默认不轮询、不展示 echo 内容，仅保留任务执行阶段关键字段的展示与刷新。 |

**实现要点**（前端）：

- 列表：若后端改为不返回 summary，则列表不再使用 summary；表格列仅保留必要元数据 + 可选 4 项统计。
- 详情：移除所有“回显原文”展示区块；保留并突出“运行状态”卡片（4 项）；刷新时仅拉取详情 + progress（运行中），不拉 echo。
- 后端（可选）：列表接口返回 `to_dict()` 时对 `summary` 置为 `null` 或省略；详情接口在“仅要关键字段”的场景下也可不返回 summary，或仅返回 strix_stats 等（按实现简单度二选一）。

---

## 四、接口与数据流（优化后）

| 阶段     | 数据来源           | 前端展示 |
|----------|--------------------|----------|
| 运行中   | GET .../progress   | 仅 4 项：模型、漏洞数、Agents、Tools（+ 刷新/取消）；**不轮询**，用户点击刷新时读一次展示即可（progress 仅在 1/3/5 分钟与结束时更新）。 |
| 运行中   | live_echo.txt       | 不展示；可选“查看完整回显”时再读 GET .../echo。 |
| 结束后   | task.summary（DB） | 不展示原文；仅 4 项可从 strix_stats 展示。 |
| 结束后   | live_echo.txt       | 仅当用户主动“查看回显”时使用。 |

**json 不一直读**：progress.json 仅在 1/3/5 分钟与任务结束时由后端各写一次；前端在 txt 复写并更新 progress 之后**按需读一次**（如用户点击刷新）展示即可，无需轮询或高频读。

---

## 五、实施检查清单

- [ ] **后端**：在任务执行的第 1、3、5 分钟及任务结束时各覆盖写一次 `live_echo.txt`，并用同一段内容解析后写一次 `progress.json`；运行中不再按块写 progress.json。
- [ ] **后端**：progress 解析改为“关键词 + .*(\d+)”取数字（Vulnerabilities、Agents、Tools），ANSI 剥离保留；两处解析逻辑一致（strix_runner + strix_integration）。
- [ ] **后端**（可选）：列表接口不返回 summary 或返回 null；详情接口按需精简返回字段。
- [ ] **前端**：列表不展示回显相关内容，仅保留关键列。
- [ ] **前端**：详情仅保留“运行状态”4 项 + 基础信息 + 报告/取消等操作，移除所有回显原文展示；不轮询；刷新时读一次 progress 展示即可。
- [ ] **文档**：更新《渗透测试回显实现说明》中 live_echo 的触发方式为“1/3/5 分钟 + 结束各写一次”。

---

## 六、小结

- **Txt**：由“一直回显写入”改为**第 1/3/5 分钟 + 结束各覆盖写一次**（共最多 4 次），每次写完后用同一内容解析并写一次 progress.json；既能在运行中拿到阶段回显与进度，又显著降低 IO。
- **progress.json**：**不按块实时写**，仅在上述 4 个时间点各写一次；前端**不一直读**，在 txt 复写更新之后按需读一次展示即可。
- **正则**：以 **Vulnerabilities、Agents、Tools（及 Model）为关键词**匹配其后数字，提升鲁棒性。
- **前端**：仅保留任务执行阶段**关键字段**（模型、漏洞数、Agents、Tools）的展示，不展示大段回显，必要时再通过 echo 接口按需查看。
