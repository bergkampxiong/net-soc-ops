# DHCP 通过远程 WMI(DCOM) 从 Windows 采集并写入本地 DB（定时 + 手动同步）
# 保留 WinRM + PowerShell 脚本字符串供参考，实际采集走 WMI。
import ipaddress
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from database.ipam_models import DhcpServer, DhcpScope, DhcpLease, DhcpWmiTarget
from database.category_models import Credential, CredentialType

logger = logging.getLogger(__name__)

NS_CIMV2 = "//./root/cimv2"
NS_DHCP = "//./root/Microsoft/Windows/DHCP"

# Windows Server 2019 等使用无 MSFT_ 前缀的类名（DhcpServerv4*）；部分版本用 MSFT_DhcpServerV4* / v4*
DHCP_SCOPE_CLASS_NAMES = ("DhcpServerv4Scope", "MSFT_DhcpServerV4Scope", "MSFT_DhcpServerv4Scope")
DHCP_LEASE_CLASS_NAMES = ("DhcpServerv4Lease", "MSFT_DhcpServerV4Lease", "MSFT_DhcpServerv4Lease")
DHCP_RESERVATION_CLASS_NAMES = ("DhcpServerv4Reservation", "MSFT_DhcpServerV4Reservation", "MSFT_DhcpServerv4Reservation")

# 在 Windows 上执行的 PowerShell（原 WinRM 方案，仅作参考保留）
DHCP_COLLECT_PS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
    if (-not (Get-Module -ListAvailable -Name DHCPServer)) { throw 'DHCPServer module not found' }
    Import-Module DHCPServer -ErrorAction Stop
} catch {
    Write-Output ('{"error":"' + ($_.Exception.Message -replace '"','\"') + '"}')
    exit 1
}
$servers = @()
$scopes = @()
$leases = @()
try {
    $computerName = $env:COMPUTERNAME
    $ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' -and $_.IPAddress -notlike '169.*' } | Select-Object -First 1).IPAddress
    $scopeList = Get-DhcpServerv4Scope -ErrorAction SilentlyContinue
    $scopeCount = ($scopeList | Measure-Object).Count
    $totalIps = 0; $usedIps = 0
    foreach ($sc in $scopeList) {
        $totalIps += ($sc.EndRange - $sc.StartRange + 1)
        $addrCount = (Get-DhcpServerv4Lease -ScopeId $sc.ScopeId -ErrorAction SilentlyContinue | Measure-Object).Count
        $usedIps += $addrCount
        $mask = $sc.SubnetMask.ToString()
        $cidr = switch -Regex ($mask) { '^255\.255\.255\.255$' { 32 } '^255\.255\.255\.254$' { 31 } '^255\.255\.255\.252$' { 30 } '^255\.255\.255\.248$' { 29 } '^255\.255\.255\.240$' { 28 } '^255\.255\.255\.224$' { 27 } '^255\.255\.255\.192$' { 26 } '^255\.255\.255\.128$' { 25 } '^255\.255\.255\.0$' { 24 } '^255\.255\.254\.0$' { 23 } '^255\.255\.252\.0$' { 22 } '^255\.255\.248\.0$' { 21 } '^255\.255\.240\.0$' { 20 } '^255\.255\.224\.0$' { 19 } '^255\.255\.192\.0$' { 18 } '^255\.255\.128\.0$' { 17 } '^255\.255\.0\.0$' { 16 } default { 24 } }
        $scopes += @{ server_name = $computerName; name = $sc.Name; network_address = $sc.NetworkId.ToString(); mask_cidr = $mask + '/' + $cidr; enabled = ($sc.State -eq 2); scope_id = $sc.ScopeId.ToString(); total_ips = ($sc.EndRange - $sc.StartRange + 1); used_ips = $addrCount; available_ips = ($sc.EndRange - $sc.StartRange + 1 - $addrCount) }
    }
    $servers += @{ name = $computerName; type = 'Windows'; ip_address = $ip; failover_status = 'N/A'; num_scopes = $scopeCount; total_ips = $totalIps; used_ips = $usedIps; available_ips = ($totalIps - $usedIps); status = 'Up' }
    foreach ($sc in $scopeList) {
        $leaseList = Get-DhcpServerv4Lease -ScopeId $sc.ScopeId -ErrorAction SilentlyContinue
        foreach ($l in $leaseList) {
            $leases += @{ server_name = $computerName; scope_name = $sc.Name; ip_address = $l.IPAddress.ToString(); mac = $l.ClientId; client_name = $l.HostName; is_reservation = $false; status = $l.AddressState }
        }
        $resList = Get-DhcpServerv4Reservation -ScopeId $sc.ScopeId -ErrorAction SilentlyContinue
        foreach ($r in $resList) {
            $leases += @{ server_name = $computerName; scope_name = $sc.Name; ip_address = $r.IPAddress.ToString(); mac = $r.ClientId; client_name = $r.Name; is_reservation = $true; status = 'Reserved' }
        }
    }
} catch {
    Write-Output ('{"error":"' + ($_.Exception.Message -replace '"','\"') + '"}')
    exit 1
}
$out = @{ servers = $servers; scopes = $scopes; leases = $leases }
$json = $out | ConvertTo-Json -Depth 10 -Compress
Write-Output $json
"""


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
    """对多个 WMI 类名依次执行 SELECT 查询，返回第一个成功的行列表。where_clause 可选，如 \"WHERE ScopeId = '10.0.0.0'\"。"""
    last_exc: Optional[Exception] = None
    for cls in class_names:
        wql = f"{select_clause} FROM {cls}"
        if where_clause:
            wql = f"{wql} {where_clause}"
        try:
            return _wmi_query_rows(i_wbem_services, wql)
        except Exception as e:
            if _is_wbem_invalid_class(e):
                last_exc = e
                continue
            raise
    if last_exc is not None:
        raise last_exc
    return []


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
        svc_dhcp = level1.NTLMLogin(NS_DHCP, NULL, NULL)
        rows = _wmi_query_rows_try_classes(svc_dhcp, "SELECT ScopeId", DHCP_SCOPE_CLASS_NAMES)
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
        return True, f"WMI 连接成功（DHCP 命名空间可访问，作用域数约 {len(rows)}，主机: {cn}）"
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
        svc_dhcp = level1.NTLMLogin(NS_DHCP, NULL, NULL)

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

        scope_rows = _wmi_query_rows_try_classes(svc_dhcp, "SELECT *", DHCP_SCOPE_CLASS_NAMES)
        if not scope_rows:
            return False, "未查询到 DHCP 作用域（作用域类为空），请确认本机为 DHCP 服务器。", None

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
    """保留：通过 WinRM 执行 PowerShell（参考）。"""
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


def run_dhcp_wmi_sync(db: Session, target_id: Optional[int] = None) -> Dict[str, Any]:
    """
    从已配置的 DHCP 目标通过远程 WMI(DCOM) 采集并写入 dhcp_servers/dhcp_scopes/dhcp_leases。
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

    try:
        db.query(DhcpLease).delete()
        db.query(DhcpScope).delete()
        db.query(DhcpServer).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("清空 DHCP 表失败")
        return {"success": False, "message": "清空表失败: " + str(e), "targets_ok": 0, "targets_fail": len(targets), "error_per_target": []}

    server_name_to_id: Dict[str, int] = {}
    scope_key_to_id: Dict[str, int] = {}

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
            error_per_target.append({"target_id": t.id, "host": t.host, "error": err_msg})
            targets_fail += 1
            continue

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
