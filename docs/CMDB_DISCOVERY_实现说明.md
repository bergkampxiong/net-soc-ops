# CMDB 设备发现 — 现状与实现说明

## 1. Cisco 园区网络设备发现的后端功能完成了吗？

**已完成（本次实现）。**

- 前端在「开始发现」时请求：`POST /api/cmdb/discovery`，并提交 `discovery_type`、`ip_range`、`username`、`password`、`enable_password`（可选）、`port`、`timeout`、`threads` 等参数。
- 后端已实现 `POST /api/cmdb/discovery` 路由（`routes/cmdb/discovery.py`），并按 `discovery_type` 调度；当前支持 `cisco-campus`，通过 netmiko SSH 执行 `show version` / `show inventory` 并解析后写入 CMDB。

---

## 2. 正常的网络设备发现是否用到了前端要求填写的这些信息？

**设计上应该用，目前没有任何地方在用。**

前端收集的通用参数与业界常见的网络设备发现流程是对应的：

| 前端字段     | 用途说明 |
|-------------|----------|
| `ip_range`  | 发现范围：如 `192.168.1.0/24` 或 `192.168.1.1-192.168.1.254`，用于解析出待探测 IP 列表。 |
| `username`  | SSH 登录设备用的用户名。 |
| `password`  | SSH 登录密码（或 enable 密码，视实现而定）。 |
| `port`      | SSH 端口，默认 22。 |
| `timeout`   | 单台设备连接/执行命令超时（秒）。 |
| `threads`   | 并发探测数量，用于加速大网段发现。 |

也就是说：**正常的 Cisco 园区设备发现理应使用上述信息**：先根据 `ip_range` 得到 IP 列表，再用 `username`/`password`/`port` 对每个 IP 做 SSH 登录（或先 ping/端口探测再 SSH），执行 `show version`、`show inventory` 等命令采集设备信息，并写入 CMDB。  
当前问题是后端尚未实现该流程，所以这些参数目前**完全没有被使用**。

---

## 3. 如何实现才能满足 CMDB 使用数据库的字段要求？

### 3.1 CMDB 相关表与必填/常用字段

与「网络设备发现」直接相关的库表与字段如下（来自 `database/cmdb_models.py` 等）：

**cmdb_assets（资产主表）**

- 必填/发现时建议写入：`name`、`asset_tag`（唯一）、`ip_address`
- 建议写入：`serial_number`、`device_type_id`、`vendor_id`、`status_id`
- 可选：`version`、`notes`、`location_id`、`department_id` 等

**cmdb_network_devices（网络设备扩展表，与 Asset 一对一）**

- 建议写入：`device_model`、`os_version`、`management_ip`
- 可选：`device_role`、`console_port` 等

**依赖的基础数据（int_all_db 等已初始化）**

- `cmdb_device_types`：如 Router、Switch、Firewall 等
- `cmdb_vendors`：如 Cisco、Huawei 等
- `cmdb_asset_statuses`：如「在用」「闲置」等

发现逻辑需要根据设备类型（如 Cisco 园区交换机/路由器）解析出：**设备类型 ID**、**厂商 ID**，并选用合适的 **状态 ID**（如「在用」）。

### 3.2 实现思路（满足 CMDB 字段要求）

1. **新增后端发现接口**
   - 在 `routes/cmdb/` 下新增 discovery 路由（例如 `discovery.py`），注册 `POST /cmdb/discovery`。
   - 请求体与前端一致：`discovery_type`、`ip_range`、`username`、`password`、`port`、`timeout`、`threads` 等。
   - 返回结构可与前端约定一致，例如：`{ "success": true, "discovered_count": N, "message": "..." }`。

2. **解析 IP 范围**
   - 将 `ip_range` 解析为 IP 列表（支持 CIDR 如 `192.168.1.0/24` 或范围如 `192.168.1.1-192.168.1.254`）。
   - 可使用 `ipaddress` 或现有工具函数，注意排除全 0/全 1 等非法主机地址。

3. **按 discovery_type 分支（Cisco 园区为先）**
   - 当 `discovery_type == 'cisco-campus'`（或后续扩展的 cisco-datacenter 等）时：
     - 使用 **netmiko**（项目已在 `app/process_designer/code_generator.py` 中使用）按 `username`、`password`、`port`、`timeout` 对每个 IP 进行 SSH 连接。
     - 设备类型传 `cisco_ios` 或 `cisco_xe`（与现有 `int_all_db.py` 等处的类型一致）。
     - 执行 `show version`、`show inventory` 等，解析出：
       - 主机名 → Asset.`name`
       - 序列号 → Asset.`serial_number`
       - 型号 → NetworkDevice.`device_model`
       - 版本 → Asset.`version` 或 NetworkDevice.`os_version`
       - 管理 IP → 当前探测 IP → Asset.`ip_address`、NetworkDevice.`management_ip`
     - 并发数由 `threads` 控制（注意 netmiko 一般为同步，可用线程池或 asyncio 包装）。

4. **写入 CMDB 满足字段要求**
   - **asset_tag**：必须唯一，可用 `hostname + '_' + ip` 或 `serial_number`，若 SN 为空则用 `DISCOVER_<ip>_<timestamp>` 等规则，避免重复。
   - **device_type_id**：根据设备型号/CLI 输出映射到 `cmdb_device_types`（如 Switch、Router），查询得到 id。
   - **vendor_id**：Cisco 园区固定为 Cisco，查询 `cmdb_vendors` 中 name='Cisco' 的 id。
   - **status_id**：可选默认「在用」，查询 `cmdb_asset_statuses` 得到 id。
   - 先查是否已存在该资产（例如按 `ip_address` 或 `asset_tag`），存在则更新，否则插入。
   - 插入/更新 Asset 后，再插入或更新对应的 **NetworkDevice**（`asset_id` 关联，`device_model`、`os_version`、`management_ip` 等从发现结果填充）。

5. **错误与并发**
   - 单台超时、认证失败、非 Cisco 设备等只记录日志并跳过，不中断整次发现。
   - 返回的 `discovered_count` 为本次**新写入或更新的设备数**（或按产品约定为「成功发现数」），便于前端展示「成功发现 N 台设备」。

按上述方式实现，即可：
- 使用前端填写的所有发现参数；
- 将发现结果完整、合规地写入 CMDB 的 Asset + NetworkDevice，满足现有数据库字段要求。

---

## 4. 小结

| 问题 | 结论 |
|------|------|
| 1. Cisco 园区发现后端完成了吗？ | **未完成**，缺少 `POST /api/cmdb/discovery` 及任何发现逻辑。 |
| 2. 前端填的信息有没有被用？ | **应该被用**，且与常规网络发现流程一致；目前因后端未实现，**完全没被使用**。 |
| 3. 如何满足 CMDB 字段？ | 实现 discovery 接口 → 解析 IP → 用现有 netmiko+SSH 采集设备信息 → 按 Asset/NetworkDevice 及基础表 id 写入/更新，保证 `asset_tag` 唯一并填满必填与常用字段。 |

---

## 5. 已实现与后续开发路线图（统筹）

### 5.1 当前已实现

- **POST /api/cmdb/discovery**：请求体含 `discovery_type`、`ip_range`、`username`、`password`、`enable_password`（可选）、`port`、`timeout`、`threads`。
- **Cisco 园区网络设备发现**（`discovery_type: cisco-campus`）：IP 解析（CIDR/范围/单 IP）→ netmiko SSH（cisco_ios）→ `show version` / `show inventory` 解析 → 写入 Asset + NetworkDevice，默认状态「使用中」、厂商 Cisco、设备类型 Switch。
- **前端**：通用表单已增加「Enable 密码」输入项（可选），并随请求提交。

### 5.2 后续开发顺序（测试完 Cisco 园区后再做）

| 阶段 | 发现类型 | 说明 |
|------|----------|------|
| 1（已完成） | Cisco 园区 | 已实现，待联调与测试。 |
| 2 | Cisco 数据中心 | `cisco-datacenter`，netmiko 设备类型 `cisco_nxos`，命令与解析类似，可复用 `DiscoveredDevice` 与 `sync_discovered_to_cmdb`。 |
| 3 | 华为 / H3C / 锐捷 | `huawei`、`h3c`、`ruijie`，各写一个 runner（netmiko 设备类型 + 对应 show 命令解析），在 `registry.py` 注册。 |
| 4 | 安全设备 | `paloalto`、`fortinet`，SSH/API 采集方式可能不同，需单独实现 runner。 |
| 5 | 虚拟化与云 | `vmware`（vCenter API）、`aws`（boto3）、`aliyun`（OpenAPI），与网络设备发现流程差异大，参数已在前端区分，后端按类型实现并写入 CMDB（含 Server/VM 等模型）。 |

实现方式统一为：在 `services/discovery/` 下新增对应模块（如 `cisco_datacenter.py`、`huawei.py`），实现「参数 → List[DiscoveredDevice]」；在 `registry.py` 的 `DISCOVERY_RUNNERS` 中注册；前端已具备发现类型与表单，无需改路由。
