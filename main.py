import json
import os
import sys
import time
from PySide6.QtCore import (
    QCoreApplication,
    QSettings,
    QStandardPaths,
    QTimer,
    Qt,
    Slot,
)
try:
    from PySide6.QtGui import QAction
except ImportError:
    from PySide6.QtWidgets import QAction

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.about_dialog import AboutDialog
from src.course_manager import CourseManager
from src.updater import UpdateWorker
from src.version import get_app_version

CHECK_INTERVAL_SECONDS = 86400  # 24 hours in seconds


class CourseViewerDialog(QDialog):
    """Offline interactive viewer for embedded course lessons and syllabus."""

    def __init__(self, course_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(course_data.get("title", "Course Viewer"))
        self.resize(700, 520)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 16)

        header = QLabel(f"<h2>{course_data.get('title', 'Course')}</h2>")
        header.setStyleSheet("color: #1a237e;")
        layout.addWidget(header)

        desc = QLabel(course_data.get("description", ""))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(desc)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #ddd;")
        layout.addWidget(divider)

        lessons_title = QLabel("<b>Embedded Lessons (Offline Ready):</b>")
        layout.addWidget(lessons_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        lessons_widget = QWidget()
        lessons_layout = QVBoxLayout(lessons_widget)
        lessons_layout.setSpacing(10)

        for l in course_data.get("lessons", []):
            lesson_frame = QFrame()
            lesson_frame.setStyleSheet(
                "QFrame { background-color: #f7f9fa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; }"
            )
            lf_layout = QVBoxLayout(lesson_frame)
            lf_layout.setSpacing(6)

            l_header = QHBoxLayout()
            title = QLabel(f"<b>{l.get('title', 'Lesson')}</b>")
            title.setStyleSheet("font-size: 13px; color: #222;")
            duration = QLabel(f"⏱ {l.get('duration', '')}")
            duration.setStyleSheet("color: #666; font-size: 11px; font-weight: bold;")
            l_header.addWidget(title)
            l_header.addStretch()
            l_header.addWidget(duration)
            lf_layout.addLayout(l_header)

            content = QLabel(l.get("content", ""))
            content.setWordWrap(True)
            content.setStyleSheet("color: #444; font-size: 12px; margin-top: 4px;")
            lf_layout.addWidget(content)

            lessons_layout.addWidget(lesson_frame)

        lessons_layout.addStretch()
        scroll.setWidget(lessons_widget)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


class EnrollmentDialog(QDialog):
    """Dialog for offline course license verification using the embedded public key."""

    def __init__(self, course_manager: CourseManager, course_id: str, course_title: str, parent=None):
        super().__init__(parent)
        self.course_manager = course_manager
        self.course_id = course_id
        self.setWindowTitle(f"Enroll in {course_title}")
        self.setFixedWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info_label = QLabel(
            f"<b>Enroll in {course_title}</b><br>"
            "Enter your offline purchase payload (JSON) and cryptographic signature "
            "received after online enrollment."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        form = QFormLayout()
        self.payload_edit = QTextEdit()
        default_payload = json.dumps(
            {"course_id": course_id, "user_id": "student_offline", "valid": True},
            indent=2,
        )
        self.payload_edit.setPlainText(default_payload)
        self.payload_edit.setFixedHeight(90)
        form.addRow("License Payload (JSON):", self.payload_edit)

        self.signature_edit = QLineEdit()
        self.signature_edit.setPlaceholderText("Base64 signature from web backend...")
        form.addRow("Digital Signature:", self.signature_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        verify_btn = QPushButton("Verify & Activate Offline")
        verify_btn.setStyleSheet(
            "background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 14px;"
        )
        verify_btn.clicked.connect(self.verify_and_activate)
        btn_layout.addWidget(verify_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def verify_and_activate(self):
        try:
            payload = json.loads(self.payload_edit.toPlainText().strip())
        except Exception:
            QMessageBox.warning(self, "Invalid JSON", "The payload is not valid JSON.")
            return

        sig = self.signature_edit.text().strip()
        success = self.course_manager.verify_and_save_license(payload, sig)
        if success:
            QMessageBox.information(
                self,
                "License Activated",
                f"Course '{self.course_id}' has been unlocked and persisted to your user directory!",
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Verification Failed",
                "Cryptographic signature check failed. Ensure the signature matches the public key.",
            )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CourseApp - Offline Embedded Learning")
        self.resize(980, 700)

        # Persistent user data directory (never touched by app updates)
        self.user_data_path = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        os.makedirs(self.user_data_path, exist_ok=True)

        self.course_manager = CourseManager()

        # Layout Setup
        root_widget = QWidget()
        self.main_layout = QVBoxLayout(root_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setCentralWidget(root_widget)

        # Silent Update Notification Banner
        self.banner = QFrame()
        self.banner.setFixedHeight(40)
        self.banner.setStyleSheet(
            "background-color: #e8f4fd; border-bottom: 1px solid #c2e0f9;"
        )
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(16, 0, 16, 0)
        banner_layout.setSpacing(12)

        badge_label = QLabel("NEW UPDATE")
        badge_label.setStyleSheet(
            "background-color: #0288d1; color: white; font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 3px;"
        )
        banner_layout.addWidget(badge_label)

        self.banner_text = QLabel("A new version is available.")
        self.banner_text.setStyleSheet("color: #01579b; font-size: 12px; font-weight: bold;")
        banner_layout.addWidget(self.banner_text)

        banner_layout.addStretch()

        view_btn = QPushButton("View & Install")
        view_btn.setFixedHeight(26)
        view_btn.setStyleSheet(
            "background-color: #0288d1; color: white; border: none; border-radius: 3px; padding: 0 12px; font-size: 11px; font-weight: bold;"
        )
        view_btn.clicked.connect(self.show_about_dialog)
        banner_layout.addWidget(view_btn)

        dismiss_btn = QPushButton("✕")
        dismiss_btn.setFixedSize(22, 22)
        dismiss_btn.setStyleSheet(
            "border: none; background: transparent; color: #555; font-size: 12px;"
        )
        dismiss_btn.clicked.connect(self.banner.hide)
        banner_layout.addWidget(dismiss_btn)

        self.banner.hide()
        self.main_layout.addWidget(self.banner)

        # Main Content Area
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        self.cards_layout = QVBoxLayout(content_widget)
        self.cards_layout.setContentsMargins(24, 24, 24, 24)
        self.cards_layout.setSpacing(16)

        # Header Row
        header_row = QHBoxLayout()

        header_box = QVBoxLayout()
        headline = QLabel(
            f"CourseApp v{QCoreApplication.applicationVersion()} (Offline Desktop Player)"
        )
        headline.setStyleSheet("font-size: 18px; font-weight: bold; color: #222;")
        header_box.addWidget(headline)

        info_label = QLabel(
            f"<b>Persistent License Directory:</b> {self.user_data_path}<br>"
            "<span style='color: #666; font-size: 11px;'>"
            "When updating across versions, application binaries and embedded courses update "
            "without deleting your saved licenses in the persistent directory.</span>"
        )
        info_label.setStyleSheet("margin-top: 4px; font-size: 12px; color: #444;")
        header_box.addWidget(info_label)

        header_row.addLayout(header_box)
        header_row.addStretch()

        # Update App Button
        self.update_app_btn = QPushButton("🔄 Check for Updates")
        self.update_app_btn.setFixedHeight(34)
        self.update_app_btn.setStyleSheet(
            "QPushButton { background-color: #0288d1; color: white; font-weight: bold; font-size: 12px; padding: 0 16px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #0277bd; }"
        )
        self.update_app_btn.clicked.connect(self.trigger_manual_update_check)
        header_row.addWidget(self.update_app_btn)

        self.cards_layout.addLayout(header_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #ddd; margin: 8px 0;")
        self.cards_layout.addWidget(divider)

        # Course Cards Container
        self.courses_container = QVBoxLayout()
        self.courses_container.setSpacing(14)
        self.cards_layout.addLayout(self.courses_container)

        self.refresh_courses_ui()

        self.cards_layout.addStretch()
        content_scroll.setWidget(content_widget)
        self.main_layout.addWidget(content_scroll)

        # Menu Bar
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu.addMenu("&Help")
        update_action = QAction("&Check for Updates...", self)
        update_action.triggered.connect(self.trigger_manual_update_check)
        help_menu.addAction(update_action)

        about_action = QAction("&About CourseApp", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Silent Startup Update Check
        self.silent_worker = None
        QTimer.singleShot(1500, self.maybe_run_daily_update_check)

    def refresh_courses_ui(self):
        """Builds or refreshes the offline course display cards."""
        # Clear existing
        while self.courses_container.count():
            item = self.courses_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        courses = self.course_manager.get_courses()
        if not courses:
            empty_lbl = QLabel("No embedded courses found in assets directory.")
            empty_lbl.setStyleSheet("color: #888; font-style: italic;")
            self.courses_container.addWidget(empty_lbl)
            return

        for c in courses:
            card = self._create_course_card(c)
            self.courses_container.addWidget(card)

    def _create_course_card(self, course: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 14px; }"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # Top row: Title and Badge
        top_row = QHBoxLayout()
        title_lbl = QLabel(f"<b>{course.get('title', 'Untitled Course')}</b>")
        title_lbl.setStyleSheet("font-size: 15px; color: #1a237e;")
        top_row.addWidget(title_lbl)

        top_row.addStretch()

        is_free = course.get("is_free", False)
        course_id = course.get("course_id", "")
        is_unlocked = self.course_manager.is_course_unlocked(course_id, is_free)

        badge = QLabel()
        if is_unlocked:
            badge.setText("UNLOCKED / ENROLLED" if not is_free else "FREE STARTER")
            badge.setStyleSheet(
                "background-color: #e8f5e9; color: #2e7d32; font-weight: bold; font-size: 10px; padding: 3px 8px; border-radius: 4px; border: 1px solid #a5d6a7;"
            )
        else:
            badge.setText("ENROLLMENT REQUIRED")
            badge.setStyleSheet(
                "background-color: #fff3e0; color: #e65100; font-weight: bold; font-size: 10px; padding: 3px 8px; border-radius: 4px; border: 1px solid #ffcc80;"
            )
        top_row.addWidget(badge)
        layout.addLayout(top_row)

        # Description
        desc_lbl = QLabel(course.get("description", ""))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(desc_lbl)

        # Lessons overview
        lessons = course.get("lessons", [])
        if lessons:
            lesson_txt = "Lessons: " + " • ".join([l.get("title", "") for l in lessons])
            lesson_lbl = QLabel(lesson_txt)
            lesson_lbl.setStyleSheet("color: #777; font-size: 11px;")
            layout.addWidget(lesson_lbl)

        # Bottom action button
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if is_unlocked:
            play_btn = QPushButton("Open Offline Course")
            play_btn.setStyleSheet(
                "background-color: #1976d2; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
            )
            play_btn.clicked.connect(
                lambda checked, c=course: self.open_course_view(c)
            )
            btn_row.addWidget(play_btn)
        else:
            enroll_btn = QPushButton("Activate / Enter License")
            enroll_btn.setStyleSheet(
                "background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
            )
            enroll_btn.clicked.connect(
                lambda checked, cid=course_id, ct=course.get("title"): self.show_enrollment_dialog(cid, ct)
            )
            btn_row.addWidget(enroll_btn)

        layout.addLayout(btn_row)
        return card

    def show_enrollment_dialog(self, course_id: str, title: str):
        dlg = EnrollmentDialog(self.course_manager, course_id, title, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_courses_ui()

    def open_course_view(self, course_data: dict):
        dlg = CourseViewerDialog(course_data, self)
        dlg.exec()

    @Slot()
    def trigger_manual_update_check(self):
        """Directly triggers the update flow and opens the About dialog to show progress."""
        dialog = AboutDialog(self)
        dialog.start_update_check()
        dialog.exec()

    @Slot()
    def maybe_run_daily_update_check(self):
        settings = QSettings()
        last_check = settings.value(
            "updater/last_check_timestamp", 0, type=int
        )
        now = int(time.time())

        if (now - last_check) < CHECK_INTERVAL_SECONDS:
            return

        self.silent_worker = UpdateWorker(mode="check")
        self.silent_worker.update_available.connect(self.on_silent_update_found)
        self.silent_worker.update_available.connect(self._record_check_time)
        self.silent_worker.no_update.connect(self._record_check_time)
        self.silent_worker.start()

    @Slot()
    def _record_check_time(self, *args):
        settings = QSettings()
        settings.setValue("updater/last_check_timestamp", int(time.time()))

    @Slot(str, str, str)
    def on_silent_update_found(self, new_version: str, download_url: str, release_notes: str):
        self.banner_text.setText(f"Version {new_version} is available!")
        self.banner.show()

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()


def main():
    app = QApplication(sys.argv)
    QCoreApplication.setOrganizationName("AdaTheCoder")
    QCoreApplication.setApplicationName("CourseApp")

    current_version = get_app_version()
    QCoreApplication.setApplicationVersion(current_version)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
