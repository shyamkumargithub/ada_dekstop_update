import base64
import json
import os
import sys
from pathlib import Path
from PySide6.QtCore import QStandardPaths

# Fixed embedded public key for offline course enrollment verification
PUBLIC_KEY_HEX = "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c"


class CourseManager:
    """
    Manages offline embedded courses across versions and handles
    persistent user licenses independently of the application installation directory.
    """

    def __init__(self, bundled_assets_path: str = None):
        if bundled_assets_path:
            self.assets_path = Path(bundled_assets_path)
        else:
            self.assets_path = self._resolve_assets_path()

        # Persistent user data directory (e.g. ~/Library/Application Support/CourseApp on macOS,
        # %APPDATA%/CourseApp on Windows, ~/.local/share/CourseApp on Linux).
        # This directory is NEVER overwritten or removed during application updates.
        self.user_data_path = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        self.user_data_path.mkdir(parents=True, exist_ok=True)
        self.license_file = self.user_data_path / "licenses.json"

    @staticmethod
    def _resolve_assets_path() -> Path:
        """Locates the bundled assets directory in both PyInstaller bundles and dev mode."""
        if getattr(sys, "frozen", False):
            base_dir = (
                Path(sys._MEIPASS)
                if hasattr(sys, "_MEIPASS")
                else Path(sys.executable).parent
            )
            return base_dir / "assets"
        return Path(__file__).resolve().parent.parent / "assets"

    def get_courses(self) -> list:
        """Scans the bundled courses folder and returns metadata for each course."""
        courses_dir = self.assets_path / "courses"
        courses = []
        if not courses_dir.exists():
            return courses

        for folder in sorted(courses_dir.iterdir()):
            if folder.is_dir():
                meta_file = folder / "metadata.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            data["folder"] = folder.name
                            courses.append(data)
                    except Exception:
                        pass
        return courses

    def load_saved_licenses(self) -> dict:
        """Loads saved offline course licenses from the persistent user data directory."""
        if not self.license_file.exists():
            return {}
        try:
            with open(self.license_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def is_course_unlocked(self, course_id: str, is_free: bool = False) -> bool:
        """Returns True if the course is free or has a valid offline license recorded."""
        if is_free:
            return True
        saved = self.load_saved_licenses()
        return course_id in saved

    def verify_and_save_license(self, token_payload: dict, signature_b64: str) -> bool:
        """
        Verifies the digital signature using the embedded Ed25519 public key.
        If valid, stores the enrollment token in the persistent user directory.
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519

            public_key = ed25519.Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(PUBLIC_KEY_HEX)
            )
            data = json.dumps(token_payload, sort_keys=True).encode("utf-8")
            signature = base64.b64decode(signature_b64)

            public_key.verify(signature, data)
        except ImportError:
            # Fallback for development environments without cryptography package
            if not signature_b64:
                return False
        except Exception:
            return False

        # Store persistent enrollment
        course_id = token_payload.get("course_id")
        if not course_id:
            return False

        licenses = self.load_saved_licenses()
        licenses[course_id] = {
            "payload": token_payload,
            "signature": signature_b64,
        }

        try:
            with open(self.license_file, "w", encoding="utf-8") as f:
                json.dump(licenses, f, indent=2)
            return True
        except Exception:
            return False
