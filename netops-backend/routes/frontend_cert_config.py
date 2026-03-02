# 前端证书配置 API：自签名生成或导入 CA 证书，写入前端使用的目录
import os
import subprocess
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.frontend_cert_config_models import FrontendCertConfig

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/system",
    tags=["system"],
    responses={404: {"description": "Not found"}},
)

# 前端证书写入目录（环境变量 FRONTEND_CERT_DIR，默认项目内 netops-frontend/.cert）
def _get_cert_dir() -> str:
    base = os.environ.get("FRONTEND_CERT_DIR", "").strip()
    if base:
        return base
    # 默认：backend 同级目录下的 netops-frontend/.cert
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parent = os.path.dirname(backend_dir)
    return os.path.join(parent, "netops-frontend", ".cert")


class CertConfigResponse(BaseModel):
    cert_mode: str
    validity_days: Optional[int] = None
    enable_https: bool
    has_ca_cert: bool  # 是否已存在证书文件（可用于 ca_import 或自签名生成后）


class CertConfigUpdate(BaseModel):
    cert_mode: str  # self_signed | ca_import
    validity_days: Optional[int] = None
    enable_https: Optional[bool] = None
    cert_pem: Optional[str] = None  # CA 证书内容，ca_import 时必填
    key_pem: Optional[str] = None   # 私钥内容，ca_import 时必填


@router.get("/cert-config", response_model=CertConfigResponse)
def get_cert_config(db: Session = Depends(get_db)):
    """获取前端证书配置；has_ca_cert 表示磁盘上是否已有证书文件。"""
    row = db.query(FrontendCertConfig).first()
    if not row:
        return CertConfigResponse(
            cert_mode="self_signed",
            validity_days=3650,
            enable_https=False,
            has_ca_cert=False,
        )
    cert_dir = _get_cert_dir()
    key_path = os.path.join(cert_dir, "key.pem")
    cert_path = os.path.join(cert_dir, "cert.pem")
    has_ca_cert = os.path.isfile(key_path) and os.path.isfile(cert_path)
    return CertConfigResponse(
        cert_mode=row.cert_mode or "self_signed",
        validity_days=row.validity_days,
        enable_https=row.enable_https or False,
        has_ca_cert=has_ca_cert,
    )


def _ensure_cert_dir() -> str:
    cert_dir = _get_cert_dir()
    os.makedirs(cert_dir, mode=0o700, exist_ok=True)
    return cert_dir


def _generate_self_signed(cert_dir: str, validity_days: int) -> None:
    key_path = os.path.join(cert_dir, "key.pem")
    cert_path = os.path.join(cert_dir, "cert.pem")
    try:
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", key_path,
                "-out", cert_path,
                "-subj", "/CN=localhost",
                "-days", str(validity_days),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        logger.exception("openssl 生成自签名证书失败: %s", e.stderr)
        raise HTTPException(status_code=500, detail="生成自签名证书失败，请确认已安装 openssl")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="未找到 openssl，请先安装 openssl")


@router.put("/cert-config")
def update_cert_config(body: CertConfigUpdate, db: Session = Depends(get_db)):
    """
    更新前端证书配置并执行实际操作：
    - self_signed：按 validity_days 生成自签名证书并写入前端证书目录，保存后需重启前端服务生效。
    - ca_import：将 cert_pem、key_pem 写入前端证书目录，保存后需重启前端服务生效。
    """
    cert_mode = (body.cert_mode or "").strip().lower() or "self_signed"
    if cert_mode not in ("self_signed", "ca_import"):
        raise HTTPException(status_code=400, detail="cert_mode 须为 self_signed 或 ca_import")

    row = db.query(FrontendCertConfig).first()
    if not row:
        row = FrontendCertConfig(cert_mode=cert_mode, validity_days=3650, enable_https=False)
        db.add(row)

    cert_dir = _ensure_cert_dir()
    key_path = os.path.join(cert_dir, "key.pem")
    cert_path = os.path.join(cert_dir, "cert.pem")

    if cert_mode == "self_signed":
        validity_days = body.validity_days if body.validity_days is not None else (row.validity_days or 3650)
        if validity_days < 1 or validity_days > 36500:
            raise HTTPException(status_code=400, detail="validity_days 须在 1～36500 之间")
        _generate_self_signed(cert_dir, validity_days)
        row.cert_mode = "self_signed"
        row.validity_days = validity_days
    else:
        if not body.cert_pem or not body.key_pem:
            raise HTTPException(status_code=400, detail="导入 CA 证书时须提供 cert_pem 与 key_pem")
        try:
            with open(cert_path, "w") as f:
                f.write(body.cert_pem)
            with open(key_path, "w") as f:
                f.write(body.key_pem)
            os.chmod(key_path, 0o600)
        except OSError as e:
            logger.exception("写入证书文件失败: %s", e)
            raise HTTPException(status_code=500, detail="写入证书文件失败")
        row.cert_mode = "ca_import"
        row.validity_days = None

    if body.enable_https is not None:
        row.enable_https = body.enable_https
    db.commit()
    return {"ok": True, "message": "证书已更新，请重启前端服务使 HTTPS 生效。"}


@router.put("/cert-config/upload")
async def update_cert_config_upload(
    cert_mode: str = Form(...),
    validity_days: Optional[int] = Form(None),
    enable_https: Optional[str] = Form(None),
    cert_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """通过上传文件导入 CA 证书（cert_file、key_file 为 PEM 文件）。"""
    cert_mode = cert_mode.strip().lower() or "ca_import"
    if cert_mode != "ca_import":
        raise HTTPException(status_code=400, detail="上传接口仅用于 ca_import 模式")
    cert_pem = (await cert_file.read()).decode("utf-8", errors="replace")
    key_pem = (await key_file.read()).decode("utf-8", errors="replace")
    enable_https_bool = enable_https is not None and str(enable_https).strip().lower() in ("true", "1", "yes")
    return update_cert_config(
        CertConfigUpdate(cert_mode="ca_import", cert_pem=cert_pem, key_pem=key_pem, enable_https=enable_https_bool),
        db,
    )
