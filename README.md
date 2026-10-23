# CourseApp - PySide6 Offline Course Management & In-App Auto-Updater

A production-grade, cross-platform desktop application built with **Python & PySide6 (Qt for Python)**. Features embedded offline courses, Ed25519 public-key cryptographic license verification, persistent user state across updates, and an automated multi-platform distribution pipeline (`.exe`, `.dmg`, `.deb`) via **GitHub Actions** and **PyInstaller**.

---

## 📑 Table of Contents
1. [Architecture & System Flow Overview](#1-architecture--system-flow-overview)
2. [Flow 1: Decoupled User State & Offline Course Bundling](#2-flow-1-decoupled-user-state--offline-course-bundling)
3. [Flow 2: Public-Key Cryptographic License Enrollment](#3-flow-2-public-key-cryptographic-license-enrollment)
4. [Flow 3: Automated Cross-Platform CI/CD Pipeline](#4-flow-3-automated-cross-platform-cicd-pipeline)
5. [Flow 4: First-Time Download & Installation](#5-flow-4-first-time-download--installation)
6. [Flow 5: How In-App Auto-Updates Work](#6-flow-5-how-in-app-auto-updates-work)
7. [Flow 6: Release Lifecycle Walkthrough (V1 to V2)](#7-flow-6-release-lifecycle-walkthrough-v1-to-v2)
8. [Local Development & Testing](#8-local-development--testing)
9. [Project File Structure](#9-project-file-structure)

---

## 1. Architecture & System Flow Overview

```
+-----------------------------------------------------------------------------------------+
|                                    DEVELOPER WORKFLOW                                   |
|                                                                                         |
|  1. Add Course Content           2. Push Git Tag (v1.0.0)      3. GitHub Actions Matrix |
|     (assets/courses/course_2)  -->   git push origin v1.0.0 -->   - Windows: Inno Setup |
|                                                                   - macOS:   hdiutil    |
|                                                                   - Ubuntu:  dpkg-deb   |
+-----------------------------------------------------------------------------------------+
                                                                             |
                                                                             v
+-----------------------------------------------------------------------------------------+
|                                  DISTRIBUTION ON GITHUB                                 |
|                                                                                         |
|  - GitHub Releases:  CourseApp-v1.0.0-Windows-Setup.exe                                 |
|                      CourseApp-v1.0.0-macOS.dmg                                         |
|                      CourseApp-v1.0.0-amd64.deb                                         |
|  - GitHub Raw:       version.json (Auto-updated with URLs & release notes on 'main')    |
+-----------------------------------------------------------------------------------------+
                                                                             |
                                                                             v
+-----------------------------------------------------------------------------------------+
|                                   USER'S DESKTOP APP                                    |
|                                                                                         |
|  +-----------------------------------------------------------------------------------+  |
|  | Installation Directory (Overwritten on updates)                                   |  |
|  | - CourseApp binary (PyInstaller)                                                  |  |
|  | - assets/courses/ (Embedded Course 1, Course 2, etc.)                             |  |
|  +-----------------------------------------------------------------------------------+  |
|                                                                                         |
|  +-----------------------------------------------------------------------------------+  |
|  | Persistent User Data Directory (NEVER wiped or modified by updates)               |  |
|  | - QStandardPaths.AppDataLocation/licenses.json (Saved Ed25519 offline licenses)   |  |
|  +-----------------------------------------------------------------------------------+  |
|                                                                                         |
|  +-----------------------------------------------------------------------------------+  |
|  | In-App Auto-Updater                                                               |  |
|  | - Silent 24-hour startup check against version.json via QSettings                |  |
|  | - Notification banner: "[NEW UPDATE] Version X available! [View & Install]"       |  |
|  | - About Dialog: View release notes, stream download progress, silent install      |  |
|  +-----------------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Flow 1: Decoupled User State & Offline Course Bundling

When distributing desktop software that contains large offline content (e.g. video courses, exercises, or interactive modules), the application separates read-only course data from user enrollment state:

### 1. Application Installation Directory
- **Location**: `C:\Program Files\CourseApp` (Windows) or `/Applications/CourseApp.app` (macOS) or `/opt/courseapp` (Linux).
- **Contents**: Python binary, Qt libraries, and bundled course data inside `assets/courses/`.
- **Update Behavior**: When the user installs a new version (e.g., upgrading from Version 1 to Version 2), this directory is replaced with the new build.

### 2. Persistent User Data Directory
- **Location**: Resolved dynamically using `QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)`:
  - **Windows**: `%APPDATA%\CourseApp\` (e.g. `C:\Users\<user>\AppData\Roaming\AdaTheCoder\CourseApp\`)
  - **macOS**: `~/Library/Application Support/AdaTheCoder/CourseApp/`
  - **Linux**: `~/.local/share/CourseApp/`
- **Contents**: `licenses.json` (unlocked course IDs, purchase payloads, and cryptographic signatures).
- **Update Behavior**: Operating system installers **never touch** this directory during upgrades. All unlocked courses remain accessible after updating to Version 2.

---

## 3. Flow 2: Public-Key Cryptographic License Enrollment

When a user purchases a course online and needs to access it inside the desktop app completely offline:

```
[Web Backend (Online)]
   |
   | 1. User purchases Course 2 online
   | 2. Backend generates JSON payload:
   |    {"course_id": "course_2", "user_id": "student_123", "valid": true}
   | 3. Backend signs payload using Ed25519 Private Key
   | 4. User receives (Payload JSON, Base64 Signature)
   v
[Desktop App (Offline)]
   |
   | 5. User clicks "Activate / Enter License" on Course 2
   | 6. CourseManager verifies signature with embedded PUBLIC_KEY_HEX
   | 7. Valid license is stored in persistent licenses.json
   v
[Course 2 Unlocked Offline permanently]
```

- **Verification Code**: Implemented in [`src/course_manager.py`](file:///Users/maks/Documents/antigravity/friendly-goodall/src/course_manager.py).
- **Cryptographic Algorithm**: Ed25519 (high-speed, 32-byte keys, tamper-proof signature verification).
- **Fallback**: Works both with the `cryptography` Python package and in lightweight development environments.

---

## 4. Flow 3: Automated Cross-Platform CI/CD Pipeline

The GitHub Actions workflow [`.github/workflows/build-release.yml`](file:///Users/maks/Documents/antigravity/friendly-goodall/.github/workflows/build-release.yml) automates multi-platform packaging:

```
Push Git Tag (v1.0.0)
         |
         +----------------------------------+----------------------------------+
         |                                  |                                  |
         v                                  v                                  v
[windows-latest]                     [macos-latest]                     [ubuntu-latest]
1. Setup Python 3.11                 1. Setup Python 3.11               1. Setup Python 3.11
2. Inject src/_version.py            2. Inject src/_version.py          2. Inject src/_version.py
3. Generate version_info.txt         3. PyInstaller bundle              3. Install GUI system libs
4. PyInstaller build                 4. Native hdiutil creates          4. PyInstaller bundle
5. Choco install Inno Setup             CourseApp-v1.0.0-macOS.dmg      5. dpkg-deb creates
6. Compile ISCC installer                                                  CourseApp-v1.0.0-amd64.deb
   CourseApp-v1.0.0-Windows-Setup.exe
         |                                  |                                  |
         +----------------------------------+----------------------------------+
                                            |
                                            v
                                  [Release Job (Ubuntu)]
                       1. Download all artifacts (merge-multiple: true)
                       2. Publish GitHub Release with all 3 binaries
                       3. Generate release notes via GitHub CLI (gh api)
                       4. Update version.json on 'main' branch
                       5. Commit and push version.json [skip ci]
```

---

## 5. Flow 4: First-Time Download & Installation

Users download the initial application directly from the repository's GitHub Releases page:

👉 **[https://github.com/shyamkumargithub/ada_dekstop_update/releases](https://github.com/shyamkumargithub/ada_dekstop_update/releases)**

### Installation Instructions by Platform

#### Windows:
1. Download `CourseApp-vX.Y.Z-Windows-Setup.exe`.
2. Double-click to launch the Inno Setup installer.
3. Follow the wizard (installs to user directory, creates Desktop & Start Menu shortcuts).
4. Launch **CourseApp**.

#### macOS:
1. Download `CourseApp-vX.Y.Z-macOS.dmg`.
2. Double-click the DMG file to mount it.
3. Drag `CourseApp.app` into the **Applications** shortcut folder.
4. Launch from Applications or Launchpad.

#### Linux (Ubuntu/Debian):
1. Download `CourseApp-vX.Y.Z-amd64.deb`.
2. Open terminal and run:
   ```bash
   sudo dpkg -i CourseApp-vX.Y.Z-amd64.deb
   # Or install dependencies automatically:
   sudo apt install ./CourseApp-vX.Y.Z-amd64.deb
   ```
3. Launch `CourseApp` from your application menu or run `courseapp` in the terminal.

---

## 6. Flow 5: How In-App Auto-Updates Work

Once installed, users **never need to visit GitHub manually for updates**.

### 1. Silent Startup Check (Throttled to Once Every 24 Hours)
- Whenever `CourseApp` launches, it reads `updater/last_check_timestamp` from `QSettings`.
- If fewer than 86,400 seconds (24 hours) have passed since the last check, the startup check is skipped.
- When due, a non-blocking background thread (`UpdateWorker`) fetches `version.json` from GitHub.
- If a newer version exists (e.g. `v2.0.0 > v1.0.0`), a notification banner appears at the top of the UI:
  ```
  [NEW UPDATE] Version 2.0.0 is available!  [View & Install]  [✕]
  ```

### 2. Manual On-Demand Check
- Click **Help** → **About CourseApp** in the menu bar.
- Click **"Check for Updates"**.
- The app checks `version.json`. If a new release is available, the changelog / release notes appear in the dialog, and the button changes to **"Download & Install"**.

### 3. One-Click Silent Download & Install
- Clicking **"Download & Install"** streams the installer into the OS temporary directory while updating a progress bar.
- Upon completion, `apply_update_and_exit()` executes the native installer:
  - **Windows**: Runs `CourseApp-vX.Y.Z-Windows-Setup.exe /SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS` and cleanly quits the app.
  - **macOS**: Mounts the DMG and opens Finder so the user can drag the updated app.
  - **Linux**: Triggers `pkexec apt install --reinstall -y <installer.deb>`.

---

## 7. Flow 6: Release Lifecycle Walkthrough (V1 to V2)

Here is how you release a new version with new offline course content:

### Step 1: Add New Embedded Course Content
Create a new folder inside `assets/courses/course_2/` and add `metadata.json`:
```json
{
  "course_id": "course_2",
  "title": "Course 2: Advanced Offline Application Architecture",
  "description": "Offline embedded course bundled in Version 2.",
  "is_free": false
}
```

### Step 2: Commit Changes
```bash
git add .
git commit -m "feat: embed Course 2 offline content"
git push origin main
```

### Step 3: Tag and Push the New Version
```bash
git tag v2.0.0
git push origin v2.0.0
```

### Step 4: Automated CI/CD Execution
- GitHub Actions triggers automatically on the `v2.0.0` tag.
- Compiles the Windows `.exe`, macOS `.dmg`, and Ubuntu `.deb` packages.
- Creates GitHub Release `v2.0.0` with all 3 binaries attached.
- Auto-generates release notes and updates `version.json` on the `main` branch:
  ```json
  {
    "version": "2.0.0",
    "release_notes": "Added Course 2 with offline embedded content and UI improvements.",
    "windows": { "url": ".../CourseApp-v2.0.0-Windows-Setup.exe" },
    "macos": { "url": ".../CourseApp-v2.0.0-macOS.dmg" },
    "linux": { "url": ".../CourseApp-v2.0.0-amd64.deb" }
  }
  ```

### Step 5: User Updates In-App
- Existing users running Version 1.0.0 see the update notification banner.
- Clicking **"View & Install"** downloads Version 2.0.0.
- After installation, Course 2 appears in their app.
- Any previously purchased licenses stored in `licenses.json` remain valid and unlocked!

---

## 8. Local Development & Testing

### 1. Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Application in Development Mode
```bash
python main.py
```

### 3. Build Windows Executable Locally
```powershell
pyinstaller --noconfirm --onedir --windowed --name "CourseApp" --icon "assets/icon.ico" --add-data "assets;assets" main.py
iscc /DMyAppVersion=1.0.0 installer.iss
```

### 4. Build macOS DMG Locally
```bash
pyinstaller --noconfirm --onedir --windowed --name "CourseApp" --add-data "assets:assets" main.py
hdiutil create -volname "CourseApp" -srcfolder "dist/CourseApp.app" -ov -format UDZO "dist/CourseApp-1.0.0-macOS.dmg"
```

### 5. Build Ubuntu DEB Locally
```bash
pyinstaller --noconfirm --onedir --windowed --name "courseapp" --add-data "assets:assets" main.py
# Place dist files into build_deb/opt/courseapp and package:
dpkg-deb --build --root-owner-group build_deb dist/CourseApp-1.0.0-amd64.deb
```

---

## 9. Project File Structure

```plaintext
.
├── .github/
│   └── workflows/
│       └── build-release.yml    # GitHub Actions cross-platform matrix CI/CD
├── assets/
│   ├── icon.ico                 # 32x32 multi-platform application icon
│   └── courses/
│       ├── course_1/            # Embedded Course 1 (Free starter course)
│       │   └── metadata.json
│       └── course_2/            # Embedded Course 2 (Requires license verification)
│           └── metadata.json
├── src/
│   ├── __init__.py
│   ├── about_dialog.py          # About dialog with system info & updater controls
│   ├── course_manager.py        # Offline course loader & Ed25519 license verification
│   ├── updater.py               # Background UpdateWorker thread & native installer execution
│   └── version.py               # Dynamic Git tag version resolver
├── .gitignore                   # Ignore rules for PyInstaller, build dirs, and venvs
├── installer.iss                # Inno Setup Windows installer configuration
├── main.py                      # Main PySide6 application window & course browser
├── requirements.txt             # PySide6, pyinstaller, packaging, cryptography
├── version.json                 # Distribution release metadata & platform download URLs
└── README.md                    # Complete architectural & operational guide
```
