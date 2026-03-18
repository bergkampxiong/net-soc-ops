# DHCP 通过远程 WMI(DCOM) 从 Windows 采集并写入本地 DB（定时 + 手动同步）
# 保留 WinRM + PowerShell 脚本字符串供参考，实际采集走 WMI。
import ipaddress
import json
import logging
import re
import socket
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from database.ipam_models import DhcpServer, DhcpScope, DhcpLease, DhcpWmiTarget
from database.category_models import Credential, CredentialType

logger = logging.getLogger(__name__)

# pywinrm 要求 read_timeout_sec 必须严格大于 operation_timeout_sec
WINRM_DHCP_SCOPE_PHASE_OPERATION_SEC = 600
WINRM_DHCP_SCOPE_PHASE_READ_SEC = 720
WINRM_DHCP_PER_SCOPE_OPERATION_SEC = 600
WINRM_DHCP_PER_SCOPE_READ_SEC = 720
WINRM_LEASE_DETAIL_MAX_ADDRESSES = 12000
WINRM_LEASE_DETAIL_FALLBACK_MAX_POOL = 16384
# 同机多路 WinRM 易拥塞，降为 2 路并行
WINRM_LEASE_FETCH_MAX_WORKERS = 2

_DEBUG_DHCP_LOG = "/app/net-soc-ops/.cursor/debug-e86f26.log"


def _dhcp_debug_log(message: str, data: Dict[str, Any]) -> None:
    """失败时写入 NDJSON，便于对照（不含密码）。"""
    try:
        row = {"sessionId": "e86f26", "message": message, "timestamp": int(time.time() * 1000), **data}
        with open(_DEBUG_DHCP_LOG, "a", encoding="utf-8") as df:
            df.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _winrm_tcp_probe(host: str, port: int, timeout_sec: float = 10.0) -> Optional[str]:
    """对 WinRM 端口做 TCP 探测；失败返回错误文案，成功返回 None。"""
    try:
        with socket.create_connection((host.strip(), int(port)), timeout=timeout_sec):
            pass
        return None
    except OSError as e:
        return str(e)[:200]


def _is_transient_winrm_timeout(exc: BaseException) -> bool:
    """仅识别真实网络/HTTP 读超时，勿把 pywinrm 参数校验（文案含 timeout）当超时。"""
    s = str(exc)
    if "read_timeout_sec must exceed" in s or "operation_timeout_sec" in s and "must exceed" in s:
        return False
    try:
        from requests.exceptions import ConnectTimeout, ReadTimeout

        if isinstance(exc, (ReadTimeout, ConnectTimeout)):
            return True
    except ImportError:
        pass
    sl = s.lower()
    return "read timed out" in sl or "connection timed out" in sl


def _winrm_try_parse_dhcp_json(raw_out: bytes) -> Optional[dict]:
    """从 WinRM 标准输出中提取 DHCP 采集结果 JSON（忽略前后杂行）。"""
    if not raw_out:
        return None
    text = raw_out.decode("utf-8", errors="replace").strip()
    candidates = [text] + [ln.strip() for ln in text.splitlines() if ln.strip() and ln.strip().startswith("{")]
    for chunk in reversed(candidates):
        try:
            d = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        if "scopes" in d and "servers" in d:
            return d
        if d.get("error") is not None and len(d) <= 2:
            return d
    return None


# 远程 WMI 读 DHCP 时，impacket 未设置 RPC_C_IMP_LEVEL_IMPERSONATE，DHCP 提供程序常返回 0 实例；
# SolarWinds 等产品实际采用「WinRM + DCOM 回退」。故 WMI 无数据时自动尝试 WinRM(PowerShell) 采集。
# 另：StdRegProv 读注册表需 ExecMethod，impacket 未暴露，未实现。

NS_CIMV2 = "//./root/cimv2"
NS_DHCP = "//./root/Microsoft/Windows/DHCP"
DHCP_NAMESPACE_CANDIDATES = (
    "//./root/Microsoft/Windows/DHCP",
    "//./root/Microsoft/Windows/DHCPv2",
    "//./root/Microsoft/Windows/DHCPv4",
    "//./root/Microsoft/Windows",
)

# Windows Server 2019 等使用无 MSFT_ 前缀的类名（DhcpServerv4*）；部分版本用 MSFT_DhcpServerV4* / v4*
DHCP_SCOPE_CLASS_NAMES = ("DhcpServerv4Scope", "MSFT_DhcpServerV4Scope", "MSFT_DhcpServerv4Scope")
DHCP_LEASE_CLASS_NAMES = ("DhcpServerv4Lease", "MSFT_DhcpServerV4Lease", "MSFT_DhcpServerv4Lease")
DHCP_RESERVATION_CLASS_NAMES = ("DhcpServerv4Reservation", "MSFT_DhcpServerV4Reservation", "MSFT_DhcpServerv4Reservation")

# WinRM 阶段 1：仅 Get-DhcpServerv4Scope + 池大小，不调用 ScopeStatistics（WinRM 下易慢/超时）
DHCP_COLLECT_PS_SCOPES_STATS = r"""$ProgressPreference='SilentlyContinue';$VerbosePreference='SilentlyContinue';$WarningPreference='SilentlyContinue';$ErrorActionPreference='Stop'
try{Import-Module DHCPServer -EA Stop|Out-Null}catch{Write-Output ('{"error":"'+($_.Exception.Message -replace '"','\"')+'"}');exit 1}
$s=@();$c=@()
try{
$n=$env:COMPUTERNAME
$ip=$null;try{$w=Get-WmiObject -Class Win32_NetworkAdapterConfiguration -EA SilentlyContinue|Where-Object{$_.IPEnabled}|Select-Object -First 1;if($w){$ip=@($w.IPAddress)|Where-Object{$_ -match '^\d+\.\d+' -and $_ -notlike '169.*'}|Select-Object -First 1}}catch{}
$raw=Get-DhcpServerv4Scope -EA SilentlyContinue
$sa=@();if($raw){if($raw -is [array]){$sa=$raw}else{$sa=@($raw)}}
$tot=0
foreach($sc in $sa){
if(-not $sc -or -not $sc.StartRange -or -not $sc.EndRange){continue}
$sr=$sc.StartRange.ToString();$er=$sc.EndRange.ToString()
$sb=[System.Net.IPAddress]::Parse($sr).GetAddressBytes();[Array]::Reverse($sb);$su=[BitConverter]::ToUInt32($sb,0);$eb=[System.Net.IPAddress]::Parse($er).GetAddressBytes();[Array]::Reverse($eb);$eu=[BitConverter]::ToUInt32($eb,0);$r=[int64]$eu-[int64]$su+1
$tot+=$r
$m=if($sc.SubnetMask){$sc.SubnetMask.ToString()}else{'255.255.255.0'}
$cidr=(([System.Net.IPAddress]::Parse($m).GetAddressBytes()|ForEach-Object{[convert]::ToString($_,2).Replace('0','')})-join'').Length
$na=if($sc.NetworkId){$sc.NetworkId.ToString()}elseif($sc.ScopeId){$sc.ScopeId.ToString()}else{''}
$scopeId=if($sc.ScopeId){$sc.ScopeId.ToString()}else{$na}
$sn=if($null -ne $sc.Name -and '' -ne [string]$sc.Name){[string]$sc.Name}else{$scopeId}
$c+=@{server_name=$n;name=$sn;network_address=$na;mask_cidr=$m+'/'+$cidr;enabled=($sc.State -eq 2);scope_id=$scopeId;total_ips=$r;used_ips=0;available_ips=$r;statistics_ok=$false}
}
$s+=@{name=$n;type='Windows';ip_address=$ip;failover_status='N/A';num_scopes=$sa.Count;total_ips=$tot;used_ips=0;available_ips=$tot;status='Up'}
}catch{Write-Output ('{"error":"'+($_.Exception.Message -replace '"','\"')+'"}');exit 1}
(@{servers=$s;scopes=$c}|ConvertTo-Json -Depth 10 -Compress)
"""

# 按作用域拉租约（<<<SID>>> 等为占位，运行前替换）
_DHCP_LEASES_PS_TEMPLATE = r"""$ProgressPreference='SilentlyContinue';$ErrorActionPreference='Stop'
try{Import-Module DHCPServer -EA Stop|Out-Null}catch{Write-Output ('{"error":"'+($_.Exception.Message -replace '"','\"')+'"}');exit 1}
$sid='<<<SID>>>';$scn='<<<SCN>>>';$srv='<<<SRV>>>';$l=@()
foreach($x in Get-DhcpServerv4Lease -ScopeId $sid -EA SilentlyContinue){
$ipa=if($x.IPAddress){$x.IPAddress.ToString()}else{''}
$mac=if($null -ne $x.ClientId){[string]$x.ClientId}else{''}
$hn=if($null -ne $x.HostName){[string]$x.HostName}else{''}
$st=if($null -ne $x.AddressState){[string]$x.AddressState}else{''}
if($ipa){$l+=@{server_name=$srv;scope_name=$scn;ip_address=$ipa;mac=$mac;client_name=$hn;is_reservation=$false;status=$st}}
}
foreach($x in Get-DhcpServerv4Reservation -ScopeId $sid -EA SilentlyContinue){
$ipa=if($x.IPAddress){$x.IPAddress.ToString()}else{''}
$mac=if($null -ne $x.ClientId){[string]$x.ClientId}else{''}
$nm=if($null -ne $x.Name){[string]$x.Name}else{''}
if($ipa){$l+=@{server_name=$srv;scope_name=$scn;ip_address=$ipa;mac=$mac;client_name=$nm;is_reservation=$true;status='Reserved'}}
}
if($l.Count-eq0){'[]'}else{ConvertTo-Json -InputObject @($l) -Depth 8 -Compress}
"""


def _winrm_ps_escape_single(value: str) -> str:
    """PowerShell 单引号字符串内对单引号转义。"""
    return (value or "").replace("'", "''")


def _dhcp_winrm_leases_ps_script(scope_id: str, scope_name: str, server_name: str) -> str:
    return (
        _DHCP_LEASES_PS_TEMPLATE.replace("<<<SID>>>", _winrm_ps_escape_single(scope_id))
        .replace("<<<SCN>>>", _winrm_ps_escape_single(scope_name or ""))
        .replace("<<<SRV>>>", _winrm_ps_escape_single(server_name or ""))
    )


def _winrm_parse_lease_batch_json(raw_out: bytes) -> Tuple[List[dict], Optional[str]]:
    """解析单作用域租约 JSON 数组；失败返回 ([], 错误信息)。"""
    if not raw_out:
        return [], None
    text = raw_out.decode("utf-8", errors="replace").strip()
    if text.startswith("{") and '"error"' in text:
        try:
            d = json.loads(text)
            if isinstance(d, dict) and d.get("error"):
                return [], str(d["error"])[:400]
        except json.JSONDecodeError:
            pass
    try:
        v = json.loads(text)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)], None
        if isinstance(v, dict):
            return [v], None
    except json.JSONDecodeError:
        pass
    return [], (text[:400] or "租约 JSON 无效")


def _mask_to_cidr(mask: str) -> int:
    """子网掩码点分十进制转前缀长度。"""
    m = (mask or "").strip()
    table = {
        "255.255.255.255": 32, "255.255.255.254": 31, "255.255.255.252": 30,
        "255.255.255.248": 29, "255.255.255.240": 28, "255.255.255.224": 27,
        "255.255.255.192": 26, "255.255.255.128": 25, "255.255.255.0": 24,
        "255.255.254.0": 23, "255.255.252.0": 22, "255.255.248.0": 21,
        "255.255.240.0": 20, "255.255.224.0": 19, "255.255.192.0": 18,
        "255.255.128.0": 17, "255.255.0.0": 16,
    }
    return table.get(m, 24)


def _wmi_cell_to_py(val: Any) -> Any:
    """impacket WMI 单元格转为 Python 标量。"""
    if val is None:
        return None
    if isinstance(val, list):
        if len(val) == 0:
            return None
        if len(val) == 1:
            return _wmi_cell_to_py(val[0])
        return [_wmi_cell_to_py(x) for x in val]
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8", errors="replace")
        except Exception:
            return str(val)
    return val


def _wmi_query_rows(i_wbem_services, wql: str) -> List[Dict[str, Any]]:
    """执行 WQL，返回属性名小写键的字典列表（便于统一读取）。"""
    rows: List[Dict[str, Any]] = []
    i_enum = i_wbem_services.ExecQuery(wql.strip())
    try:
        while True:
            try:
                p_enum = i_enum.Next(0xFFFFFFFF, 1)[0]
            except Exception as ex:
                if "S_FALSE" in str(ex) or "s_false" in str(ex).lower():
                    break
                raise
            props = p_enum.getProperties()
            row: Dict[str, Any] = {}
            for key in props:
                row[key.lower()] = _wmi_cell_to_py(props[key].get("value"))
            rows.append(row)
            p_enum.RemRelease()
    finally:
        try:
            i_enum.RemRelease()
        except Exception:
            pass
    return rows


def _is_wbem_invalid_class(ex: BaseException) -> bool:
    """是否为 WMI 无效类错误 (WBEM_E_INVALID_CLASS 0x80041010)。"""
    s = str(ex).lower()
    return "0x80041010" in str(ex) or "invalid_class" in s or "wbem_e_invalid_class" in s


def _wmi_query_rows_try_classes(
    i_wbem_services, select_clause: str, class_names: tuple, where_clause: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    对多个 WMI 类名依次执行 SELECT。若某类存在但 0 行，继续试下一类（修复：此前首个类 0 行即返回，永不尝试 MSFT_*）。
    仅当所有类均为无效类时抛出最后一次 WBEM 无效类异常。
    where_clause 可选，如 \"WHERE ScopeId = '10.0.0.0'\"。
    """
    last_invalid: Optional[Exception] = None
    saw_valid_query = False
    for cls in class_names:
        wql = f"{select_clause} FROM {cls}"
        if where_clause:
            wql = f"{wql} {where_clause}"
        try:
            rows = _wmi_query_rows(i_wbem_services, wql)
            saw_valid_query = True
            if rows:
                return rows
        except Exception as e:
            if _is_wbem_invalid_class(e):
                last_invalid = e
                continue
            raise
    if not saw_valid_query and last_invalid is not None:
        raise last_invalid
    return []


def _open_dhcp_wmi_service(level1, null_obj):
    """使用 root/Microsoft/Windows/DHCP 命名空间，若不可用则尝试其他候选。"""
    last_exc: Optional[Exception] = None
    for ns in DHCP_NAMESPACE_CANDIDATES:
        svc = None
        try:
            svc = level1.NTLMLogin(ns, null_obj, null_obj)
            _wmi_query_rows(svc, "SELECT Name FROM __NAMESPACE")
            return svc, ns
        except Exception as e:
            last_exc = e
            if svc is not None:
                try:
                    svc.RemRelease()
                except Exception:
                    pass
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("未找到可用 DHCP WMI 命名空间")


def _extract_scope_id(row: Dict[str, Any]) -> Optional[str]:
    candidates = ("scopeid", "scope_id", "networkid", "subnetaddress", "networkaddress", "id")
    for key in candidates:
        val = row.get(key)
        ip = _ipv4_to_str(val)
        if ip and re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
            return ip
    return None


def _discover_scope_rows_dynamic(svc_dhcp) -> List[Dict[str, Any]]:
    """
    动态发现 Scope 相关类，兼容部分环境中固定类无实例的情况。
    仅使用 WMI，不依赖 WinRM。
    """
    rows_out: List[Dict[str, Any]] = []
    try:
        class_rows = _wmi_query_rows(
            svc_dhcp,
            "SELECT __CLASS FROM meta_class WHERE __CLASS LIKE '%Scope%'",
        )
    except Exception:
        return rows_out

    candidate_classes: List[str] = []
    for r in class_rows:
        cn = str(r.get("__class") or "").strip()
        if not cn:
            continue
        cl = cn.lower()
        if "scope" not in cl or "dhcp" not in cl or "stat" in cl:
            continue
        candidate_classes.append(cn)

    seen_scope_ids: Set[str] = set()
    for cls_name in candidate_classes:
        try:
            class_rows_data = _wmi_query_rows(svc_dhcp, f"SELECT * FROM {cls_name}")
        except Exception:
            continue
        for r in class_rows_data:
            scope_id = _extract_scope_id(r)
            if not scope_id or scope_id in seen_scope_ids:
                continue
            seen_scope_ids.add(scope_id)
            subnet_mask = _ipv4_to_str(r.get("subnetmask")) or "255.255.255.0"
            rows_out.append(
                {
                    "scopeid": scope_id,
                    "name": str(r.get("name") or scope_id),
                    "subnetmask": subnet_mask,
                    "startrange": _ipv4_to_str(r.get("startrange")) or scope_id,
                    "endrange": _ipv4_to_str(r.get("endrange")) or scope_id,
                    "state": r.get("state", 1),
                }
            )
    return rows_out


def _ipv4_to_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", s):
        return s
    return s


def _scope_ip_range_total(start: Any, end: Any) -> int:
    try:
        a = ipaddress.IPv4Address(str(start).strip())
        b = ipaddress.IPv4Address(str(end).strip())
        return int(b) - int(a) + 1
    except Exception:
        return 0


def _wmi_release_all(dcom, level1, svc_cim, svc_dhcp):
    for s in (svc_dhcp, svc_cim):
        if s is not None:
            try:
                s.RemRelease()
            except Exception:
                pass
    if level1 is not None:
        try:
            level1.RemRelease()
        except Exception:
            pass
    if dcom is not None:
        try:
            dcom.disconnect()
        except Exception:
            pass


def _credential_to_ntlm_identity(username: str, domain: Optional[str]) -> Tuple[str, str]:
    """
    与凭证表单一致：用户名、域（可选）。
    用户名若含「域\\用户」则拆出域；若含「用户@域」且域字段为空则用 @ 右侧为 NTLM 域。
    域字段非空时优先于 @ 式中的域（显式填写为准）。
    """
    u = (username or "").strip()
    d = (domain or "").strip()
    if "\\" in u:
        left, _, right = u.partition("\\")
        left, right = left.strip(), right.strip()
        if right:
            return right, (left or d)
    if "@" in u:
        local, _, realm = u.partition("@")
        local, realm = local.strip(), realm.strip()
        if local and realm:
            return local, (d if d else realm)
    return u, d


def _dcom_remote_host_for_address(host: str) -> Optional[str]:
    """连接地址为域名时解析为 IPv4，供 DCOM remoteHost（仍可填 IP/FQDN 作 target 展示名）。"""
    h = (host or "").strip()
    if not h:
        return None
    try:
        import socket

        socket.inet_aton(h.split("%")[0])
        return None
    except OSError:
        pass
    try:
        import socket

        infos = socket.getaddrinfo(h, 135, socket.AF_INET, socket.SOCK_STREAM)
        return infos[0][4][0] if infos else None
    except Exception:
        return None


def _discover_netbios_name_via_smb(host: str, username: str, password: str, domain: str) -> Optional[str]:
    """通过 SMB(445) 协商读取目标机 NetBIOS 计算机名；本地账号用该名作为 NTLM 域常可消除 rpc_s_access_denied。"""
    try:
        from impacket.smbconnection import SMBConnection

        smb = SMBConnection("*SMBSERVER", host, sess_port=445, timeout=15)
        smb.login(username or "", password or "", domain or "")
        name = smb.getServerName()
        try:
            smb.logoff()
        except Exception:
            pass
        if not name:
            return None
        s = str(name).strip().rstrip("\x00").strip()
        return s or None
    except Exception:
        return None


def _ntlm_domain_candidates(
    host: str, ntlm_user: str, password: str, ntlm_domain: str
) -> List[str]:
    """
    NTLM 域候选：与凭证一致时仅用显式域；域为空时再试 SMB 计算机名、空、WORKGROUP。
    """
    out: List[str] = []
    seen: Set[str] = set()

    def add(x: str) -> None:
        if x in seen:
            return
        seen.add(x)
        out.append(x)

    if ntlm_domain:
        add(ntlm_domain)
    else:
        nb = _discover_netbios_name_via_smb(host, ntlm_user, password, "")
        if nb:
            add(nb)
        add("")
        add("WORKGROUP")
    return out


def _open_wmi_dcom_level1(host: str, username: str, password: str, domain: Optional[str]):
    """按凭证解析用户名/域；连接地址为 host（IP 或域名）；多认证级别与域候选消除 rpc_s_access_denied。"""
    from impacket.dcerpc.v5.dcom import wmi
    from impacket.dcerpc.v5.dcomrt import DCOMConnection
    from impacket.dcerpc.v5.rpcrt import (
        RPC_C_AUTHN_LEVEL_CONNECT,
        RPC_C_AUTHN_LEVEL_PKT_INTEGRITY,
        RPC_C_AUTHN_LEVEL_PKT_PRIVACY,
    )

    nuser, ndom = _credential_to_ntlm_identity(username, domain)
    remote_ip = _dcom_remote_host_for_address(host)
    dcom_target = host.strip()
    auth_levels = (
        RPC_C_AUTHN_LEVEL_CONNECT,
        RPC_C_AUTHN_LEVEL_PKT_INTEGRITY,
        RPC_C_AUTHN_LEVEL_PKT_PRIVACY,
    )
    last_exc: Optional[Exception] = None
    for auth_level in auth_levels:
        for dom in _ntlm_domain_candidates(host, nuser, password, ndom):
            dcom = None
            try:
                dcom = DCOMConnection(
                    dcom_target,
                    nuser,
                    password or "",
                    dom,
                    "",
                    "",
                    None,
                    None,
                    None,
                    authLevel=auth_level,
                    oxidResolver=True,
                    doKerberos=False,
                    kdcHost=None,
                    remoteHost=remote_ip,
                )
                iface = dcom.CoCreateInstanceEx(wmi.CLSID_WbemLevel1Login, wmi.IID_IWbemLevel1Login)
                level1 = wmi.IWbemLevel1Login(iface)
                logger.info(
                    "WMI DCOM 已连接 target=%s remoteHost=%s 域=%r auth=%s",
                    dcom_target,
                    remote_ip or "(同target)",
                    dom if dom else "(空)",
                    auth_level,
                )
                return dcom, level1
            except Exception as e:
                last_exc = e
                if dcom is not None:
                    try:
                        dcom.disconnect()
                    except Exception:
                        pass
                err_low = str(e).lower()
                if "access_denied" in err_low or "rpc_s_access_denied" in err_low:
                    continue
                raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("WMI DCOM: 无法建立连接")


def test_wmi_connection(
    host: str,
    username: str,
    password: str,
    domain: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    测试远程 WMI(DCOM) 是否可访问 DHCP 提供程序命名空间。
    port/use_ssl 为接口兼容由调用方传入，此处忽略。
    """
    try:
        from impacket.dcerpc.v5.dtypes import NULL
    except ImportError:
        return False, "未安装 impacket，请执行: pip install impacket"

    dcom = None
    level1 = None
    try:
        dcom, level1 = _open_wmi_dcom_level1(host, username, password, domain)
        svc_dhcp, ns_used = _open_dhcp_wmi_service(level1, NULL)
        rows = _wmi_query_rows_try_classes(svc_dhcp, "SELECT ScopeId", DHCP_SCOPE_CLASS_NAMES)
        if not rows:
            try:
                rows = _wmi_query_rows(svc_dhcp, "SELECT ScopeId FROM DhcpServerv4ScopeStatistics")
            except Exception:
                rows = []
        if not rows:
            rows = _discover_scope_rows_dynamic(svc_dhcp)
        try:
            svc_dhcp.RemRelease()
        except Exception:
            pass
        cn = host
        try:
            svc_cim = level1.NTLMLogin(NS_CIMV2, NULL, NULL)
            name_rows = _wmi_query_rows(svc_cim, "SELECT Name FROM Win32_ComputerSystem")
            if name_rows:
                cn = name_rows[0].get("name") or host
            svc_cim.RemRelease()
        except Exception:
            pass
        return True, f"WMI 连接成功（命名空间: {ns_used}，作用域数约 {len(rows)}，主机: {cn}）"
    except Exception as e:
        err = str(e)
        logger.exception("WMI 测试异常 host=%s", host)
        el = err.lower()
        if "timed out" in el or "timeout" in el:
            return False, f"WMI 连接超时：请检查到 {host} 的 TCP 135 及 RPC 端口是否放行。"
        if "rpc_s_server_unavailable" in el or "unavailable" in el or "refused" in el:
            return False, f"无法通过 DCOM 连接 {host}：请确认远程已启用 WMI、防火墙放行 135/RPC。"
        if "rpc_s_access_denied" in el or ("access_denied" in el and "dcom" not in el):
            return False, (
                "DCOM 拒绝访问(rpc_s_access_denied)：若为目标机本地账号，请在凭证「域」填写该服务器 NetBIOS 计算机名；"
                "域账号请填 AD NetBIOS 域名。并确认账号已加入目标机「分布式 COM 用户」且允许远程 WMI。"
            )
        if "logon" in el or "access" in el or "denied" in el or "status_logon_failure" in el:
            return False, "WMI 认证失败：请检查用户名、密码及域是否正确，且账号有 DHCP 服务器读取权限。"
        if _is_wbem_invalid_class(e):
            return False, "目标机 DHCP 命名空间中未找到已知作用域类（MSFT_DhcpServerV4Scope/v4Scope）：请确认已安装 DHCP 服务器角色且为 Windows Server 2012 或更高。"
        if "invalid class" in el or "wbem" in el:
            return False, "目标机 WMI 类不可用：请确认已安装 DHCP 服务器角色且系统版本支持。"
        return False, f"WMI 连接失败: {err[:500]}"
    finally:
        if level1 is not None:
            try:
                level1.RemRelease()
            except Exception:
                pass
        if dcom is not None:
            try:
                dcom.disconnect()
            except Exception:
                pass


def _collect_dhcp_via_remote_wmi(
    host: str,
    username: str,
    password: str,
    domain: Optional[str] = None,
) -> Tuple[bool, str, Optional[dict]]:
    """通过 WMI 采集 DHCP，返回与原 PowerShell JSON 同构的 dict。"""
    try:
        from impacket.dcerpc.v5.dtypes import NULL
    except ImportError:
        return False, "未安装 impacket，请执行: pip install impacket", None

    dcom = None
    level1 = None
    svc_cim = None
    svc_dhcp = None
    try:
        dcom, level1 = _open_wmi_dcom_level1(host, username, password, domain)
        svc_cim = level1.NTLMLogin(NS_CIMV2, NULL, NULL)
        svc_dhcp, dhcp_ns_used = _open_dhcp_wmi_service(level1, NULL)

        comp_rows = _wmi_query_rows(svc_cim, "SELECT Name FROM Win32_ComputerSystem")
        computer_name = (comp_rows[0].get("name") if comp_rows else None) or host

        ip_rows = _wmi_query_rows(
            svc_cim,
            "SELECT IPAddress FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled = TRUE",
        )
        server_ip = None
        for r in ip_rows:
            ips = r.get("ipaddress")
            if isinstance(ips, list):
                for ip in ips:
                    s = _ipv4_to_str(ip)
                    if s and not s.startswith("127.") and not s.startswith("169."):
                        server_ip = s
                        break
            else:
                s = _ipv4_to_str(ips)
                if s and not s.startswith("127.") and not s.startswith("169."):
                    server_ip = s
                    break
            if server_ip:
                break
        if not server_ip:
            server_ip = host

        _SCOPE_COLS = "ScopeId, Name, SubnetMask, StartRange, EndRange, State"
        scope_rows = []
        try:
            _ex_rows = _wmi_query_rows(
                svc_dhcp, f"SELECT {_SCOPE_COLS} FROM DhcpServerv4Scope"
            )
            if _ex_rows:
                scope_rows = _ex_rows
        except Exception:
            pass
        if not scope_rows:
            scope_rows = _wmi_query_rows_try_classes(svc_dhcp, "SELECT *", DHCP_SCOPE_CLASS_NAMES)
        if not scope_rows:
            stat_rows: List[Dict[str, Any]] = []
            try:
                stat_rows = _wmi_query_rows(svc_dhcp, "SELECT * FROM DhcpServerv4ScopeStatistics")
            except Exception:
                stat_rows = []
            if stat_rows:
                for r in stat_rows:
                    sid_raw = r.get("scopeid")
                    sid = _ipv4_to_str(sid_raw)
                    if isinstance(sid_raw, (bytes, bytearray)):
                        try:
                            sid = sid_raw.decode("utf-16-le", errors="ignore").split("\x00")[0].strip() or sid
                        except Exception:
                            pass
                    if not sid or not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", str(sid).strip()):
                        continue
                    sid = str(sid).strip()
                    sm = _ipv4_to_str(r.get("subnetmask")) or "255.255.255.0"
                    scope_rows.append({
                        "scopeid": sid,
                        "name": str(r.get("name") or sid),
                        "subnetmask": sm,
                        "startrange": sid,
                        "endrange": sid,
                        "state": 1,
                    })
                logger.info("DHCP WMI 通过 ScopeStatistics 回退得到 %s 个作用域 host=%s", len(scope_rows), host)
        if not scope_rows:
            scope_rows = _discover_scope_rows_dynamic(svc_dhcp)
            if scope_rows:
                logger.info(
                    "DHCP WMI 通过动态类发现得到 %s 个作用域 host=%s namespace=%s",
                    len(scope_rows),
                    host,
                    dhcp_ns_used,
                )
        if not scope_rows:
            return (
                False,
                (
                    f"目标 {host} 的 WMI 中 IPv4 作用域为 0（命名空间 {dhcp_ns_used}）。"
                    "将尝试 WinRM 回退；若未配置或回退失败，请在目标机启用 WinRM(5985) 并在本系统 DHCP 目标中填写端口。"
                ),
                None,
            )

        scopes_out: List[dict] = []
        leases_out: List[dict] = []
        total_ips_all = 0
        used_ips_all = 0

        for sc in scope_rows:
            scope_id = _ipv4_to_str(sc.get("scopeid")) or ""
            name = str(sc.get("name") or scope_id or "default")
            mask = _ipv4_to_str(sc.get("subnetmask")) or "255.255.255.0"
            start_r = sc.get("startrange")
            end_r = sc.get("endrange")
            total = _scope_ip_range_total(start_r, end_r)
            if total <= 0:
                total = 256
            state = sc.get("state")
            try:
                st = int(state) if state is not None else 1
            except Exception:
                st = 1
            # WMI：1 常为 Active，2 常为 Disabled（与部分文档一致）
            enabled = st != 2

            try:
                lease_rows = _wmi_query_rows_try_classes(
                    svc_dhcp, "SELECT *", DHCP_LEASE_CLASS_NAMES,
                    where_clause=f"WHERE ScopeId = '{scope_id}'",
                )
            except Exception:
                lease_rows = []
            try:
                res_rows = _wmi_query_rows_try_classes(
                    svc_dhcp, "SELECT *", DHCP_RESERVATION_CLASS_NAMES,
                    where_clause=f"WHERE ScopeId = '{scope_id}'",
                )
            except Exception:
                res_rows = []

            addr_count = len(lease_rows)
            used_ips_all += addr_count
            total_ips_all += total

            cidr = _mask_to_cidr(mask)
            network_addr = scope_id
            scopes_out.append({
                "server_name": computer_name,
                "name": name,
                "network_address": network_addr,
                "mask_cidr": f"{mask}/{cidr}",
                "enabled": enabled,
                "scope_id": scope_id,
                "total_ips": total,
                "used_ips": addr_count,
                "available_ips": max(0, total - addr_count),
            })

            for lr in lease_rows:
                ip_a = _ipv4_to_str(lr.get("ipaddress")) or ""
                leases_out.append({
                    "server_name": computer_name,
                    "scope_name": name,
                    "ip_address": ip_a,
                    "mac": lr.get("clientid") or "",
                    "client_name": lr.get("hostname") or "",
                    "is_reservation": False,
                    "status": str(lr.get("addressstate") or ""),
                })
            for rr in res_rows:
                ip_a = _ipv4_to_str(rr.get("ipaddress")) or ""
                leases_out.append({
                    "server_name": computer_name,
                    "scope_name": name,
                    "ip_address": ip_a,
                    "mac": rr.get("clientid") or "",
                    "client_name": rr.get("name") or "",
                    "is_reservation": True,
                    "status": "Reserved",
                })

        servers_out = [{
            "name": computer_name,
            "type": "Windows",
            "ip_address": server_ip,
            "failover_status": "N/A",
            "num_scopes": len(scope_rows),
            "total_ips": total_ips_all,
            "used_ips": used_ips_all,
            "available_ips": max(0, total_ips_all - used_ips_all),
            "status": "Up",
        }]
        return True, "", {"servers": servers_out, "scopes": scopes_out, "leases": leases_out}
    except Exception as e:
        logger.exception("WMI 采集 DHCP 异常 host=%s", host)
        return False, str(e)[:800], None
    finally:
        _wmi_release_all(dcom, level1, svc_cim, svc_dhcp)


def test_winrm_connection(
    host: str,
    port: int,
    username: str,
    password: str,
    domain: Optional[str] = None,
    use_ssl: bool = False,
) -> tuple[bool, str]:
    """保留：WinRM 测试（当前凭证测试已改为 WMI，此函数供参考）。"""
    try:
        import winrm
    except ImportError:
        return False, "未安装 pywinrm，请执行: pip install pywinrm"
    winrm_user = (domain.strip() + "\\" + username.strip()) if (domain and domain.strip()) else (username or "")
    endpoint = ("https" if use_ssl else "http") + "://" + host + ":" + str(port) + "/wsman"
    try:
        session = winrm.Session(
            endpoint,
            auth=(winrm_user, password or ""),
            transport="ntlm" if winrm_user else "plaintext",
            server_cert_validation="ignore" if use_ssl else None,
        )
        r = session.run_ps("Write-Output $env:COMPUTERNAME")
        if r.status_code != 0:
            err = (r.std_err or r.std_out or "脚本执行失败").decode("utf-8", errors="replace")
            return False, err or "连接失败"
        out = (r.std_out or b"").decode("utf-8", errors="replace").strip()
        return True, "连接成功" + (f"（主机: {out}）" if out else "")
    except Exception as e:
        err_msg = str(e)
        if "timed out" in err_msg or "Timeout" in err_msg:
            return False, f"连接超时：无法在限定时间内连到 {host}:{port}，请检查网络、防火墙及目标机 WinRM 服务是否启用。"
        if "Connection refused" in err_msg or "refused" in err_msg.lower():
            return False, f"连接被拒绝：{host}:{port} 未开放或 WinRM 未监听，请确认端口与 WinRM 配置。"
        if "No route" in err_msg or "Network is unreachable" in err_msg:
            return False, f"网络不可达：无法访问 {host}，请检查网络或主机地址。"
        return False, err_msg


def _run_winrm(host: str, port: int, username: str, password: str, use_ssl: bool, script: str) -> tuple[bool, str, Optional[dict]]:
    """通过 WinRM 执行 PowerShell，返回解析后的 JSON。"""
    try:
        import winrm
    except ImportError:
        return False, "未安装 pywinrm，请执行: pip install pywinrm", None
    endpoint = ("https" if use_ssl else "http") + "://" + host + ":" + str(port) + "/wsman"
    try:
        session = winrm.Session(
            endpoint,
            auth=(username or "", password or ""),
            transport="ntlm" if username else "plaintext",
            server_cert_validation="ignore" if use_ssl else None,
        )
        r = session.run_ps(script)
        if r.status_code != 0:
            return False, (r.std_err or r.std_out or "脚本执行失败").decode("utf-8", errors="replace"), None
        out = (r.std_out or b"").decode("utf-8", errors="replace").strip()
        if not out:
            return False, "脚本无输出", None
        if out.strip().startswith("{"):
            err_obj = json.loads(out)
            if "error" in err_obj:
                return False, err_obj["error"], None
        data = json.loads(out)
        return True, "", data
    except json.JSONDecodeError as e:
        return False, "JSON 解析失败: " + str(e), None
    except Exception as e:
        logger.exception("WinRM 执行异常")
        return False, str(e), None


def _collect_dhcp_via_winrm_powershell(
    host: str,
    port: int,
    use_ssl: bool,
    username: str,
    password: str,
    domain: Optional[str],
) -> Tuple[bool, str, Optional[dict]]:
    """
    阶段 1：枚举作用域；阶段 2：按作用域拉租约（池过大跳过明细）；用量由租约条数回写。
    """
    try:
        import winrm
    except ImportError:
        return False, "未安装 pywinrm，无法 WinRM 回退", None
    d = (domain or "").strip()
    u = (username or "").strip()
    winrm_user = f"{d}\\{u}" if d and u else (u or "")
    endpoint = f"{'https' if use_ssl else 'http'}://{host}:{port}/wsman"
    sess_kw: Dict[str, Any] = {
        "auth": (winrm_user, password or ""),
        "transport": "ntlm" if winrm_user else "plaintext",
        "server_cert_validation": "ignore" if use_ssl else None,
    }

    def _session(read_sec: int, op_sec: int) -> Any:
        # pywinrm：HTTP 读超时须大于 WS-Man OperationTimeout
        if read_sec <= op_sec:
            read_sec = op_sec + 120
        return winrm.Session(
            endpoint,
            read_timeout_sec=read_sec,
            operation_timeout_sec=op_sec,
            **sess_kw,
        )

    try:
        tcp_err = _winrm_tcp_probe(host, port, 10.0)
        if tcp_err:
            _dhcp_debug_log("winrm_tcp_probe_fail", {"host": host, "port": port, "error": tcp_err})
            return False, (
                f"采集机到 {host}:{port} TCP 探测失败（{tcp_err}）。"
                "请在后端主机放通出站 WinRM；勿与办公电脑连通性混淆。"
            ), None
        t0 = time.monotonic()
        session = _session(WINRM_DHCP_SCOPE_PHASE_READ_SEC, WINRM_DHCP_SCOPE_PHASE_OPERATION_SEC)
        r = session.run_ps(DHCP_COLLECT_PS_SCOPES_STATS.strip())
        phase1_elapsed = time.monotonic() - t0
        logger.info(
            "WinRM DHCP 阶段1 host=%s 耗时=%.1fs status=%s 输出字节=%s",
            host,
            phase1_elapsed,
            r.status_code,
            len(r.std_out or b""),
        )
        data = _winrm_try_parse_dhcp_json(r.std_out or b"")
        if isinstance(data, dict) and data.get("error") is not None and "scopes" not in data:
            return False, str(data["error"])[:800], None
        if not data or not isinstance(data.get("scopes"), list):
            err = (r.std_err or b"").decode("utf-8", errors="replace").strip()
            err = err or (r.std_out or b"").decode("utf-8", errors="replace")[:800]
            return False, err or "WinRM 阶段1 无有效作用域 JSON", None
        scopes_list = data["scopes"]
        if not scopes_list and r.status_code == 0:
            return False, "WinRM 已执行但 scopes 为空（目标机 Get-DhcpServerv4Scope 无结果）", data
        if not scopes_list:
            err = (r.std_out or b"").decode("utf-8", errors="replace")[:800]
            return False, err or "作用域列表为空", None

        all_leases: List[dict] = []
        to_fetch: List[dict] = []
        skipped_large: List[str] = []

        for sc in scopes_list:
            tot_pool = int(sc.get("total_ips") or 0) or 0
            used = int(sc.get("used_ips") or 0) or 0
            st_ok = sc.get("statistics_ok") is True or str(sc.get("statistics_ok")).lower() in ("true", "1")
            if st_ok and used > WINRM_LEASE_DETAIL_MAX_ADDRESSES:
                skipped_large.append(str(sc.get("name") or sc.get("scope_id") or "?"))
                continue
            if not st_ok and tot_pool > WINRM_LEASE_DETAIL_FALLBACK_MAX_POOL:
                skipped_large.append(str(sc.get("name") or sc.get("scope_id") or "?") + "(地址池过大未拉明细)")
                continue
            to_fetch.append(sc)

        lease_errors: List[str] = []

        def _fetch_leases_one(sc_row: dict) -> Tuple[List[dict], Optional[str]]:
            sid = str(sc_row.get("scope_id") or "")
            ps = _dhcp_winrm_leases_ps_script(sid, str(sc_row.get("name") or ""), str(sc_row.get("server_name") or ""))
            for lease_attempt in range(2):
                try:
                    s2 = _session(WINRM_DHCP_PER_SCOPE_READ_SEC, WINRM_DHCP_PER_SCOPE_OPERATION_SEC)
                    rr = s2.run_ps(ps)
                    break
                except BaseException as ex:
                    if lease_attempt == 0 and _is_transient_winrm_timeout(ex):
                        time.sleep(5)
                        continue
                    return [], str(ex)[:200]
            else:
                return [], "租约 WinRM 重试耗尽"
            rows, perr = _winrm_parse_lease_batch_json(rr.std_out or b"")
            if perr:
                return [], perr
            if rr.status_code != 0 and not rows:
                es = (rr.std_err or b"").decode("utf-8", errors="replace").strip()[:200]
                return [], es or f"exit={rr.status_code}"
            return rows, None

        if to_fetch:
            t1 = time.monotonic()
            n_workers = max(1, min(WINRM_LEASE_FETCH_MAX_WORKERS, len(to_fetch)))
            with ThreadPoolExecutor(max_workers=n_workers) as ex:
                futures = [ex.submit(_fetch_leases_one, sc) for sc in to_fetch]
                for fut in as_completed(futures):
                    rows, err = fut.result()
                    if err:
                        lease_errors.append(err[:150])
                    else:
                        all_leases.extend(rows)
            logger.info(
                "WinRM DHCP 阶段2 host=%s 作用域数=%s 并行=%s 耗时=%.1fs 租约条数=%s 异常数=%s",
                host,
                len(to_fetch),
                n_workers,
                time.monotonic() - t1,
                len(all_leases),
                len(lease_errors),
            )

        if lease_errors and not all_leases and to_fetch:
            return False, "WinRM 租约阶段失败: " + "; ".join(lease_errors[:4]), None

        # 阶段2 拉到的租约条数回写作用域用量（Statistics 失败时阶段1 曾为 0）
        _lease_cnt: Dict[Tuple[str, str], int] = defaultdict(int)
        for le in all_leases:
            _lease_cnt[(str(le.get("server_name") or ""), str(le.get("scope_name") or ""))] += 1
        _tot_u = 0
        for sc in scopes_list:
            k = (str(sc.get("server_name") or ""), str(sc.get("name") or ""))
            n = _lease_cnt.get(k, 0)
            if n > 0:
                sc["used_ips"] = n
                tr = int(sc.get("total_ips") or 0) or 0
                sc["available_ips"] = max(0, tr - n)
            _tot_u += int(sc.get("used_ips") or 0) or 0
        if data.get("servers") and isinstance(data["servers"], list):
            for srv in data["servers"]:
                if isinstance(srv, dict):
                    srv["used_ips"] = _tot_u
                    tt = int(srv.get("total_ips") or 0) or 0
                    srv["available_ips"] = max(0, tt - _tot_u)

        data["leases"] = all_leases
        if skipped_large:
            logger.info("WinRM DHCP 未拉租约明细的作用域: %s", skipped_large)
        if lease_errors:
            logger.warning("WinRM DHCP 部分作用域租约拉取异常: %s", lease_errors[:8])
        return True, "", data
    except json.JSONDecodeError as e:
        return False, "WinRM JSON 解析失败: " + str(e)[:400], None
    except Exception as e:
        el = str(e).lower()
        en = type(e).__name__.lower()
        # TCP 建连失败（日志里 connect timeout=720 即此类，非脚本跑得慢）
        if (
            "connecttimeout" in en
            or "connect timeout=" in el
            or ("max retries exceeded" in el and "wsman" in el and ("connect" in el or "newconnection" in el))
        ):
            _dhcp_debug_log("winrm_tcp_connect_fail", {"host": host, "port": port, "error": str(e)[:400]})
            return False, (
                f"WinRM：运行后端的机器无法与 {host}:{port} 建立 TCP（连接超时/不可达）。"
                f"请在**后端所在主机**上测试到 {host}:{port} 的连通（与浏览器所在电脑无关）；"
                "放通后端→目标的防火墙，并确认目标 Listen 5985。"
            ), None
        if "timed out" in el or "timeout" in el:
            _dhcp_debug_log(
                "winrm_final_timeout",
                {"host": host, "port": port, "error": str(e)[:500]},
            )
            return False, (
                f"WinRM 等待响应超时 {host}:{port}（读超时约 {WINRM_DHCP_SCOPE_PHASE_READ_SEC}s）。"
                "若同时出现 TCP 连不上，请先解决采集机到 5985 的路由与防火墙。"
            ), None
        if "refused" in el or "connection refused" in el:
            return False, f"WinRM 连接被拒绝 {host}:{port}，请启用 WinRM 并放行端口。", None
        logger.exception("WinRM DHCP 采集异常 host=%s", host)
        return False, str(e)[:500], None


def run_dhcp_wmi_sync(db: Session, target_id: Optional[int] = None) -> Dict[str, Any]:
    """
    从已配置的 DHCP 目标采集：先 WMI(DCOM)，作用域为 0 或失败时自动用 WinRM(PowerShell) 回退，写入 dhcp 表。
    """
    q = db.query(DhcpWmiTarget).filter(DhcpWmiTarget.enabled == True)
    if target_id is not None:
        q = q.filter(DhcpWmiTarget.id == target_id)
    targets = q.all()
    if not targets:
        return {"success": True, "message": "无启用的采集目标", "targets_ok": 0, "targets_fail": 0, "error_per_target": []}

    error_per_target: List[Dict[str, Any]] = []
    targets_ok = 0
    targets_fail = 0

    collected_batches: List[Tuple[DhcpWmiTarget, dict]] = []
    for t in targets:
        username = t.username or ""
        password = t.password or ""
        domain: Optional[str] = None
        wid = getattr(t, "windows_credential_id", None)
        if wid:
            cred = db.query(Credential).filter(Credential.id == wid, Credential.credential_type == CredentialType.WINDOWS_DOMAIN).first()
            if cred:
                username = cred.username or ""
                password = cred.password or ""
                domain = (cred.domain or "").strip() or None
        if not username and not password:
            error_per_target.append({"target_id": t.id, "host": t.host, "error": "未配置用户名密码或 Windows 凭证"})
            targets_fail += 1
            continue

        ok, err_msg, data = _collect_dhcp_via_remote_wmi(t.host, username, password, domain)
        if not ok:
            wport = int(t.port or 5985)
            wssl = bool(t.use_ssl is True)
            ok_w, err_w, data_w = _collect_dhcp_via_winrm_powershell(
                t.host, wport, wssl, username, password, domain
            )
            if ok_w and data_w:
                ok, err_msg, data = True, "", data_w
                logger.info(
                    "DHCP 已通过 WinRM 回退采集 host=%s port=%s 作用域数=%s",
                    t.host, wport, len(data_w.get("scopes") or []),
                )
            else:
                error_per_target.append({
                    "target_id": t.id,
                    "host": t.host,
                    "error": f"{err_msg}；WinRM 回退: {err_w}",
                })
                targets_fail += 1
                continue
        collected_batches.append((t, data))

    if not collected_batches:
        return {
            "success": False,
            "message": f"采集失败：{len(error_per_target)} 个目标未返回数据，已保留原有 DHCP 库表。",
            "targets_ok": 0,
            "targets_fail": targets_fail,
            "error_per_target": error_per_target,
        }

    try:
        db.query(DhcpLease).delete()
        db.query(DhcpScope).delete()
        db.query(DhcpServer).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("清空 DHCP 表失败")
        return {"success": False, "message": "清空表失败: " + str(e), "targets_ok": 0, "targets_fail": len(targets), "error_per_target": error_per_target}

    server_name_to_id: Dict[str, int] = {}
    scope_key_to_id: Dict[str, int] = {}

    for t, data in collected_batches:
        try:
            servers = data.get("servers") or []
            scopes = data.get("scopes") or []
            leases = data.get("leases") or []
            for s in servers:
                svr = DhcpServer(
                    name=s.get("name"),
                    type=s.get("type") or "Windows",
                    ip_address=s.get("ip_address"),
                    failover_status=s.get("failover_status"),
                    num_scopes=s.get("num_scopes"),
                    total_ips=s.get("total_ips"),
                    used_ips=s.get("used_ips"),
                    available_ips=s.get("available_ips"),
                    status=s.get("status"),
                )
                db.add(svr)
                db.flush()
                if svr.name:
                    server_name_to_id[svr.name] = svr.id
            db.commit()

            for sc in scopes:
                sname = sc.get("server_name")
                sid = server_name_to_id.get(sname) if sname else None
                if not sid:
                    continue
                scope = DhcpScope(
                    dhcp_server_id=sid,
                    name=sc.get("name"),
                    network_address=sc.get("network_address"),
                    mask_cidr=sc.get("mask_cidr"),
                    enabled=sc.get("enabled", True),
                    total_ips=sc.get("total_ips"),
                    used_ips=sc.get("used_ips"),
                    available_ips=sc.get("available_ips"),
                )
                db.add(scope)
                db.flush()
                scope_key_to_id[(sname or "", sc.get("name") or "")] = scope.id
            db.commit()

            for le in leases:
                sname = le.get("server_name")
                scname = le.get("scope_name")
                scope_id = scope_key_to_id.get((sname or "", scname or "")) if sname and scname else None
                if not scope_id:
                    scope_id = next((sid for (sn, sc), sid in scope_key_to_id.items() if sc == (scname or "")), None)
                if scope_id:
                    db.add(DhcpLease(
                        scope_id=scope_id,
                        ip_address=le.get("ip_address"),
                        mac=le.get("mac"),
                        client_name=le.get("client_name"),
                        is_reservation=le.get("is_reservation", False),
                        status=le.get("status"),
                    ))
            db.commit()
            if servers:
                first_name = servers[0].get("name")
                if first_name and isinstance(first_name, str):
                    t.name = first_name.strip()
                    db.commit()
            targets_ok += 1
        except Exception as e:
            db.rollback()
            logger.exception("写入 DHCP 数据失败")
            error_per_target.append({"target_id": t.id, "host": t.host, "error": str(e)})
            targets_fail += 1

    return {
        "success": targets_fail == 0,
        "message": f"成功 {targets_ok} 个目标，失败 {targets_fail} 个" if targets else "无目标",
        "targets_ok": targets_ok,
        "targets_fail": targets_fail,
        "error_per_target": error_per_target,
    }
