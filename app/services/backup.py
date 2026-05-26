import os, asyncio
from datetime import datetime
from app.core.config import settings
from app.core.logger import logger

async def create_backup() -> str | None:
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fp = os.path.join(settings.BACKUP_DIR, f"backup_{ts}.sql.gz")
    db = settings.DB_URL.replace("postgresql+asyncpg://", "postgresql://")
    proc = await asyncio.create_subprocess_shell(
        f'pg_dump "{db}" | gzip > "{fp}"',
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, err = await proc.communicate()
    if proc.returncode == 0:
        logger.info(f"Backup: {fp}"); return fp
    logger.error(f"Backup failed: {err.decode()}"); return None

async def cleanup_backups(max_files: int = 24):
    if not os.path.exists(settings.BACKUP_DIR): return
    bfiles = sorted(
        [os.path.join(settings.BACKUP_DIR, f) for f in os.listdir(settings.BACKUP_DIR) if f.endswith(".sql.gz")],
        key=os.path.getmtime
    )
    while len(bfiles) > max_files:
        os.remove(bfiles.pop(0))
