"""Standalone Windows Desktop Launcher for AI Design Studio."""
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser

STUDIO_ROOT = os.path.dirname(os.path.abspath(__file__))
if STUDIO_ROOT not in sys.path:
    sys.path.insert(0, STUDIO_ROOT)

from core.server import run_server

PORT = 8788
URL = f"http://127.0.0.1:{PORT}"


def open_app_window():
    time.sleep(1.0)
    edge = shutil.which("msedge") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    chrome = shutil.which("chrome") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    for browser in (edge, chrome):
        if browser and os.path.exists(browser):
            subprocess.Popen([browser, f"--app={URL}", "--window-size=1360,860"])
            return
    webbrowser.open(URL)


if __name__ == "__main__":
    threading.Thread(target=open_app_window, daemon=True).start()
    run_server(PORT)
