import os
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import connections


SQLITE_HEADER = b"SQLite format 3\x00"


def database_path():
    return Path(settings.DATABASES["default"]["NAME"])


def backup_dir():
    path = Path(getattr(settings, "BACKUP_DIR", database_path().parent / "backups"))
    ensure_writable(path)
    return path


def ensure_writable(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(str(path), 0o777)
    except Exception:
        pass
    return path


def ensure_file_writable(path):
    try:
        os.chmod(str(path), 0o666)
    except Exception:
        pass


def backup_filename(prefix="harinam_paper_backup"):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return "%s_%s.sqlite3" % (prefix, stamp)


def validate_sqlite_file(path):
    path = Path(path)
    if not path.exists() or path.stat().st_size < len(SQLITE_HEADER):
        return False
    with path.open("rb") as handle:
        return handle.read(len(SQLITE_HEADER)) == SQLITE_HEADER


def close_db_connections():
    try:
        connections.close_all()
    except Exception:
        pass


def create_backup(prefix="harinam_paper_backup"):
    db_path = database_path()
    if not db_path.exists():
        return None
    close_db_connections()
    folder = backup_dir()
    target = folder / backup_filename(prefix)
    shutil.copy2(str(db_path), str(target))
    ensure_file_writable(target)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            side_target = folder / (target.name + suffix)
            shutil.copy2(str(sidecar), str(side_target))
            ensure_file_writable(side_target)
    return target


def backup_database():
    return create_backup()


def recent_backups(limit=15):
    folder = backup_dir()
    files = sorted(folder.glob("*.sqlite3"), key=lambda item: item.stat().st_mtime, reverse=True)
    return files[:limit]


def restore_database_from_file(source_path):
    source_path = Path(source_path)
    if not validate_sqlite_file(source_path):
        raise ValueError("Selected file valid SQLite backup nahi hai.")
    db_path = database_path()
    ensure_writable(db_path.parent)
    create_backup("before_restore")
    close_db_connections()
    shutil.copy2(str(source_path), str(db_path))
    ensure_file_writable(db_path)
    return db_path
