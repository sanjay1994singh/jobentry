import atexit
import logging
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path


# 1. Environment & Logging Setup
def app_log_dir():
    root = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    path = Path(root) / "HarinamPress" / "HarinamPaper"
    path.mkdir(parents=True, exist_ok=True)
    return path


LOG_DIR = app_log_dir()
logging.basicConfig(
    filename=str(LOG_DIR / "server.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "harinam_paper.settings")

import django

django.setup()

from django.core.management import call_command
from waitress import serve
from harinam_paper.backup import backup_database
from harinam_paper.wsgi import application

HOST = "127.0.0.1"
PORT = 8000
_backup_done = False


def show_error_popup(message):
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Harinam Paper Error", message)
        root.destroy()
        return
    except Exception:
        pass

    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, str(message), "Harinam Paper Error", 0x10)
    except Exception:
        pass


def safe_backup_database():
    global _backup_done
    if _backup_done:
        return
    try:
        backup_database()
        _backup_done = True
    except Exception:
        log_path = LOG_DIR / "backup_error.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")


def setup_database():
    """Ensure database tables exist on fresh systems."""
    try:
        call_command("migrate", interactive=False)
    except Exception:
        log_path = LOG_DIR / "migration_error.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")


def is_server_running(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def run_server():
    serve(application, host=HOST, port=PORT, threads=4)


def open_browser():
    url = "http://%s:%s/" % (HOST, PORT)
    for _ in range(40):
        if is_server_running(HOST, PORT):
            webbrowser.open(url)
            return
        time.sleep(0.3)
    webbrowser.open(url)


def main():
    # Pehle database ready karein
    setup_database()

    atexit.register(safe_backup_database)
    threading.Thread(target=open_browser, daemon=True).start()
    run_server()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        safe_backup_database()
    except Exception:
        log_path = LOG_DIR / "startup.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        show_error_popup("Application error hua hai. Detail yahan save hai:\n%s" % log_path)
        safe_backup_database()
        raise