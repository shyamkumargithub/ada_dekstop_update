import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request
from packaging import version
from PySide6.QtCore import QCoreApplication, QThread, Signal

# Production release metadata endpoint on GitHub raw
VERSION_URL = "https://raw.githubusercontent.com/shyamkumargithub/ada_dekstop_update/main/version.json"


class UpdateWorker(QThread):
    # Signals: (new_version, download_url, release_notes)
    update_available = Signal(str, str, str)
    no_update = Signal()
    download_progress = Signal(int)
    download_finished = Signal(str)  # local installer path
    error_occurred = Signal(str)

    def __init__(self, mode="check", download_url=None):
        super().__init__()
        self.mode = mode
        self.download_url = download_url

    def run(self):
        try:
            if self.mode == "check":
                req = urllib.request.Request(
                    VERSION_URL, headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read().decode("utf-8"))

                remote_ver = data.get("version", "1.0.0")
                current_ver = QCoreApplication.applicationVersion() or "1.0.0"
                release_notes = data.get(
                    "release_notes", f"Release {remote_ver}"
                )

                # Parse versions, ignoring trailing '-dev' in comparisons if needed
                clean_current = current_ver.split("-")[0]
                if version.parse(remote_ver) > version.parse(clean_current):
                    sys_name = platform.system().lower()
                    if sys_name == "windows":
                        url = data.get("windows", {}).get("url", "")
                    elif sys_name == "darwin":
                        url = data.get("macos", {}).get("url", "")
                    else:
                        url = data.get("linux", {}).get("url", "")
                    self.update_available.emit(remote_ver, url, release_notes)
                else:
                    self.no_update.emit()

            elif self.mode == "download":
                ext = (
                    ".exe"
                    if sys.platform == "win32"
                    else (".dmg" if sys.platform == "darwin" else ".deb")
                )
                target_file = os.path.join(
                    tempfile.gettempdir(), f"CourseApp_update{ext}"
                )

                def report_hook(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = int((block_num * block_size / total_size) * 100)
                        self.download_progress.emit(min(percent, 100))

                urllib.request.urlretrieve(
                    self.download_url, target_file, reporthook=report_hook
                )
                self.download_finished.emit(target_file)

        except Exception as e:
            self.error_occurred.emit(str(e))


def apply_update_and_exit(installer_path: str):
    """Launches the native platform installer and cleanly shuts down the running app."""
    current_os = platform.system()

    if current_os == "Windows":
        # Launch Inno Setup installer silently and quit
        subprocess.Popen(
            [
                installer_path,
                "/SILENT",
                "/CLOSEAPPLICATIONS",
                "/RESTARTAPPLICATIONS",
            ]
        )
        QCoreApplication.quit()

    elif current_os == "Darwin":
        # Mount DMG and reveal in Finder
        subprocess.run(["hdiutil", "attach", installer_path])
        subprocess.run(["open", "/Volumes/CourseApp"])
        QCoreApplication.quit()

    elif current_os == "Linux":
        # Reinstall via pkexec APT UI
        cmd = f"pkexec apt install --reinstall -y {installer_path}"
        subprocess.Popen(cmd, shell=True)
        QCoreApplication.quit()
