from pathlib import Path
import shutil

from django.conf import settings
from django.db import connections


def backup_database():
    db_path = Path(settings.DATABASES["default"]["NAME"])
    if not db_path.exists():
        return None

    backup_dir = Path(getattr(settings, "BACKUP_DIR", db_path.parent / "backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / "harinam_paper_backup.sqlite3"

    try:
        connections.close_all()
    except Exception:
        pass

    shutil.copy2(str(db_path), str(backup_path))

    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            shutil.copy2(str(sidecar), str(backup_dir / ("harinam_paper_backup.sqlite3" + suffix)))

    return backup_path
