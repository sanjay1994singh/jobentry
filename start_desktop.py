import os
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path


LOG_FILE = None


def app_data_dir():
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    data_dir = Path(root) / "HarinamPress" / "HarinamPaper"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def log(message):
    if not LOG_FILE:
        return
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), message))


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(url, timeout=20):
    last_error = ""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1).close()
            return
        except urllib.error.HTTPError as exc:
            last_error = "HTTP %s: %s" % (exc.code, exc.read().decode("utf-8", errors="replace")[:1000])
            log(last_error)
        except Exception as exc:
            last_error = repr(exc)
            time.sleep(0.2)
    raise RuntimeError("Harinam Paper server did not start. Last error: %s" % last_error)


def prepare_django():
    log("Preparing Django")
    data_dir = app_data_dir()
    os.environ.setdefault("HARINAM_PAPER_DATA_DIR", str(data_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "harinam_paper.settings")
    log("Data dir: %s" % data_dir)
    if getattr(sys, "frozen", False):
        log("Frozen dir: %s" % getattr(sys, "_MEIPASS", ""))

    import django
    from django.core.management import call_command

    django.setup()
    call_command("migrate", interactive=False, verbosity=0)
    if not getattr(sys, "frozen", False):
        call_command("collectstatic", interactive=False, verbosity=0)


def start_server(port):
    try:
        log("Starting Waitress on port %s" % port)
        from waitress import serve
        from harinam_paper.wsgi import application

        serve(application, host="127.0.0.1", port=port, threads=8)
    except Exception:
        log(traceback.format_exc())
        raise


def main():
    global LOG_FILE
    LOG_FILE = app_data_dir() / "startup.log"
    LOG_FILE.write_text("", encoding="utf-8")
    log("Launching Harinam Paper")

    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).resolve().parent)
    else:
        os.chdir(Path(__file__).resolve().parent)

    try:
        prepare_django()
        port = free_port()
        url = "http://127.0.0.1:%s/" % port
        server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
        server_thread.start()
        wait_for_server(url)
        log("Server is ready")

        import webview

        webview.create_window("Harinam Paper", url, width=1500, height=900, min_size=(1050, 700))
        webview.start(debug=False)
    except Exception:
        log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
