# DHCP 通过 WinRM 从 Windows 采集并写入本地 DB（每 2 小时定时 + 手动同步）
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database.ipam_models import DhcpServer, DhcpScope, DhcpLease, DhcpWmiTarget
from database.category_models import Credential, CredentialType

logger = logging.getLogger(__name__)

# 在 Windows 上执行的 PowerShell：使用 DhcpServer 模块输出 servers/scopes/leases 的 JSON
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


def test_winrm_connection(
    host: str,
    port: int,
    username: str,
    password: str,
    domain: Optional[str] = None,
    use_ssl: bool = False,
) -> tuple[bool, str]:
    """
    测试 WinRM 连接是否可用（用于校验 Windows/域控凭证）。
    返回 (成功, 消息)。
    """
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
        # 常见网络错误：仅记简短日志，不打印完整堆栈
        if "timed out" in err_msg or "Timeout" in err_msg:
            logger.error("WinRM 测试连接超时: %s:%s", host, port)
            return False, f"连接超时：无法在限定时间内连到 {host}:{port}，请检查网络、防火墙及目标机 WinRM 服务是否启用。"
        if "Connection refused" in err_msg or "refused" in err_msg.lower():
            logger.error("WinRM 测试连接被拒绝: %s:%s", host, port)
            return False, f"连接被拒绝：{host}:{port} 未开放或 WinRM 未监听，请确认端口与 WinRM 配置。"
        if "No route" in err_msg or "Network is unreachable" in err_msg:
            logger.error("WinRM 测试网络不可达: %s", host)
            return False, f"网络不可达：无法访问 {host}，请检查网络或主机地址。"
        logger.exception("WinRM 测试异常")
        return False, err_msg


def _run_winrm(host: str, port: int, username: str, password: str, use_ssl: bool, script: str) -> tuple[bool, str, Optional[dict]]:
    """通过 WinRM 在目标机执行 PowerShell，返回 (成功, 错误信息, 解析后的 JSON)。"""
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
    从已配置的 DHCP WMI 目标通过 WinRM 采集数据并写入 dhcp_servers/dhcp_scopes/dhcp_leases。
    target_id 为 None 时处理所有启用的目标。
    返回: { "success": bool, "message": str, "targets_ok": int, "targets_fail": int, "error_per_target": [...] }
    """
    from database.ipam_models import DhcpWmiTarget

    q = db.query(DhcpWmiTarget).filter(DhcpWmiTarget.enabled == True)
    if target_id is not None:
        q = q.filter(DhcpWmiTarget.id == target_id)
    targets = q.all()
    if not targets:
        return {"success": True, "message": "无启用的采集目标", "targets_ok": 0, "targets_fail": 0, "error_per_target": []}

    error_per_target: List[Dict[str, Any]] = []
    targets_ok = 0
    targets_fail = 0

    # 先清空现有 DHCP 数据（外键顺序：leases -> scopes -> servers）
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
    scope_key_to_id: Dict[str, int] = {}  # (server_name, scope_name) -> scope_id

    for t in targets:
        username = t.username or ""
        password = t.password or ""
        wid = getattr(t, "windows_credential_id", None)
        if wid:
            cred = db.query(Credential).filter(Credential.id == wid, Credential.credential_type == CredentialType.WINDOWS_DOMAIN).first()
            if cred:
                username = cred.username or ""
                password = cred.password or ""
        ok, err_msg, data = _run_winrm(
            t.host,
            t.port or 5985,
            username,
            password,
            t.use_ssl or False,
            DHCP_COLLECT_PS_SCRIPT,
        )
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
            # 用采集到的 DHCP 服务器名称（Windows 计算机名）回写该 WMI 目标的名称
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
