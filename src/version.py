import sys
from pathlib import Path


def get_app_version() -> str:
    # 1. CI-injected version file
    try:
        from . import _version

        return _version.__version__
    except (ImportError, AttributeError):
        pass

    # 2. Bundled binary directory check
    if getattr(sys, "frozen", False):
        bundle_dir = (
            Path(sys._MEIPASS)
            if hasattr(sys, "_MEIPASS")
            else Path(sys.executable).parent
        )
        version_file = bundle_dir / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()

    # 3. Local development fallback
    return "1.0.0-dev"
