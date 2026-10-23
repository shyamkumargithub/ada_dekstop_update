# CourseApp - Cross-Platform PySide6 Offline Course Player & Updater

A production-ready desktop application built with **PySide6 (Qt for Python)** featuring offline embedded courses, public-key cryptographic license verification, persistent user state across updates, and automated cross-platform distribution pipelines (.exe, .dmg, .deb) via **GitHub Actions** and **PyInstaller**.

---

## 🌟 Key Architecture & Features

### 1. Decoupled User State & Offline Course Bundling
- **Application Assets (`assets/courses/`)**: Bundled directly with application binaries. When updated (e.g., from Version 1 with Course 1 to Version 2 with Course 2), the installation directory is replaced with new content.
- **Persistent User Data (`QStandardPaths.AppDataLocation`)**: Stores user purchase tokens, keys, and offline activation records (`licenses.json`). This directory is **never deleted or overwritten** during app updates.

### 2. Ed25519 Public-Key Offline License Verification
- Offline courses can be unlocked using an offline license payload signed by your web backend with an Ed25519 private key.
- The desktop app contains the matching **public key** (`CourseManager`), validating digital signatures locally without requiring an active internet connection.

### 3. In-App Auto-Updater & Silent Daily Check
- **24-Hour Throttling**: Checks for updates at most once every 24 hours on startup using `QSettings` (`CHECK_INTERVAL_SECONDS = 86400`).
- **Silent Background Worker**: Checks `version.json` on a separate `QThread` without blocking GUI rendering. If an update is detected, a banner notification appears with a **"NEW UPDATE"** badge.
- **Interactive About Dialog**:
  - Displays dynamic app version, Python runtime, operating system, and build type (PyInstaller bundle vs Dev mode).
  - Shows auto-generated release notes directly in the dialog.
  - Includes progress tracking and one-click **"Download & Install"**.
- **Native Platform Installers**:
  - **Windows**: Executes Inno Setup silently (`/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`).
  - **macOS**: Mounts `.dmg` via `hdiutil` and displays the application in Finder.
  - **Linux (Ubuntu)**: Triggers `pkexec apt install --reinstall -y` for `.deb` packages.

### 4. Automated CI/CD Release Pipeline
- **GitHub Actions (`.github/workflows/build-release.yml`)**:
  - Automatically triggered upon pushing version tags (e.g., `git push origin v1.0.0`).
  - Multi-OS Matrix (`windows-latest`, `macos-latest`, `ubuntu-latest`):
    - **Windows**: Dynamically generates `version_info.txt`, compiles with PyInstaller, and builds `CourseApp-vX.Y.Z-Windows-Setup.exe` with Inno Setup.
    - **macOS**: Freezes with PyInstaller and builds `CourseApp-vX.Y.Z-macOS.dmg` with `create-dmg`.
    - **Ubuntu**: Freezes with PyInstaller, generates desktop entry, and builds `CourseApp-vX.Y.Z-amd64.deb` with `dpkg-deb`.
  - **Automated `version.json` Maintenance**:
    - Generates release notes via GitHub CLI (`gh api /repos/{repo}/releases/generate-notes`).
    - Updates `version.json` with the new version number, release notes, and matrix artifact URLs.
    - Commits and pushes `version.json` back to `main` with `[skip ci]`.

---

## 📁 Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── build-release.yml    # Cross-platform matrix build & release workflow
├── assets/
│   ├── icon.ico                 # 32x32 application icon for Windows/Linux/macOS
│   └── courses/
│       ├── course_1/            # Embedded Course 1 (Free starter course)
│       │   └── metadata.json
│       └── course_2/            # Embedded Course 2 (Requires license verification)
│           └── metadata.json
├── src/
│   ├── __init__.py
│   ├── about_dialog.py          # About dialog with system info & updater UI
│   ├── course_manager.py        # Offline course loader & Ed25519 license verification
│   ├── updater.py               # Background download worker & installer executor
│   └── version.py               # Dynamic Git tag version resolver
├── .gitignore                   # Build artifacts, spec files, and cache ignores
├── installer.iss                # Inno Setup Windows installer configuration
├── main.py                      # Main PySide6 application window & course browser
├── requirements.txt             # PySide6, pyinstaller, packaging, cryptography
└── version.json                 # Distribution release metadata & download URLs
```

---

## 🚀 Quickstart & Development

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application Locally
```bash
python main.py
```

### 3. Test Offline License Enrollment
1. Launch `CourseApp`. Course 1 will show as **FREE STARTER** (Unlocked).
2. Course 2 will show as **ENROLLMENT REQUIRED**.
3. Click **"Activate / Enter License"** on Course 2.
4. Enter the license JSON and cryptographic signature to verify and unlock Course 2 offline. The license is automatically saved to your persistent AppData directory.

---

## 📦 Local Packaging

### Windows (.exe installer via Inno Setup)
```powershell
pyinstaller --noconfirm --onedir --windowed --name "CourseApp" --icon "assets/icon.ico" --add-data "assets;assets" main.py
iscc /DMyAppVersion=1.0.0 installer.iss
```

### macOS (.dmg)
```bash
pyinstaller --noconfirm --onedir --windowed --name "CourseApp" --icon "assets/icon.ico" --add-data "assets:assets" main.py
npm install -g create-dmg
create-dmg dist/CourseApp.app dist/
```

### Linux (.deb)
```bash
pyinstaller --noconfirm --onedir --windowed --name "courseapp" --add-data "assets:assets" main.py
# Build deb directory structure and package:
dpkg-deb --build --root-owner-group build_deb dist/CourseApp-v1.0.0-amd64.deb
```

---

## 🏷️ Publishing Releases via Git Tags

To build native installers for Windows, macOS, and Linux and automatically publish a GitHub Release with auto-updated `version.json`:

```bash
# 1. Commit changes
git add .
git commit -m "feat: release version 1.0.0"

# 2. Create and push Git tag
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will compile the binaries, upload them to GitHub Releases, update `version.json`, and existing desktop app users will receive the update automatically within 24 hours or via the **"Check for Updates"** button.
