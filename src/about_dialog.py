import platform
import sys
from PySide6.QtCore import QCoreApplication, Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStyle,
    QTextEdit,
    QVBoxLayout,
)

from .updater import UpdateWorker, apply_update_and_exit


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About CourseApp")
        self.setModal(True)
        self.setFixedWidth(460)

        self.worker = None
        self.download_url = None
        self.release_notes = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 16)
        root_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel()
        app_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_FileDialogInfoView
        )
        icon_label.setPixmap(app_icon.pixmap(36, 36))
        header_layout.addWidget(icon_label)

        title_container = QVBoxLayout()
        title_container.setSpacing(2)

        app_name = QCoreApplication.applicationName() or "CourseApp"
        title_label = QLabel(f"<b>{app_name}</b>")
        title_label.setStyleSheet("font-size: 15px;")

        self.app_version = QCoreApplication.applicationVersion() or "1.0.0-dev"
        subtitle_label = QLabel(f"Version {self.app_version}")
        subtitle_label.setStyleSheet("color: #666; font-size: 12px;")

        title_container.addWidget(title_label)
        title_container.addWidget(subtitle_label)
        header_layout.addLayout(title_container)
        header_layout.addStretch()

        root_layout.addLayout(header_layout)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(divider)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(4)

        os_detail = (
            f"{platform.system()} {platform.release()} ({platform.machine()})"
        )
        py_version = (
            f"{platform.python_implementation()} {platform.python_version()}"
        )
        is_bundled = (
            "PyInstaller Bundle"
            if getattr(sys, "frozen", False)
            else "Development Mode"
        )

        form_layout.addRow(self._make_key("OS:"), self._make_val(os_detail))
        form_layout.addRow(self._make_key("Python:"), self._make_val(py_version))
        form_layout.addRow(
            self._make_key("Build Type:"), self._make_val(is_bundled)
        )

        root_layout.addLayout(form_layout)

        self.status_label = QLabel("Ready to check for updates.")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        root_layout.addWidget(self.status_label)

        # Release Notes Text View (hidden until update with notes is found)
        self.notes_view = QTextEdit()
        self.notes_view.setReadOnly(True)
        self.notes_view.setFixedHeight(90)
        self.notes_view.setStyleSheet(
            "background-color: #f9f9f9; border: 1px solid #e0e0e0; font-size: 11px; padding: 4px;"
        )
        self.notes_view.hide()
        root_layout.addWidget(self.notes_view)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        root_layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)

        self.update_btn = QPushButton("Check for Updates")
        self.update_btn.clicked.connect(self.start_update_check)
        btn_layout.addWidget(self.update_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        root_layout.addLayout(btn_layout)

    @staticmethod
    def _make_key(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #777; font-size: 11px; font-weight: bold;")
        return lbl

    @staticmethod
    def _make_val(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setStyleSheet("font-size: 11px;")
        return lbl

    @Slot()
    def start_update_check(self):
        self.update_btn.setEnabled(False)
        self.status_label.setText("Checking for updates...")
        self.status_label.setStyleSheet("color: #0066cc; font-size: 11px;")
        self.notes_view.hide()

        self.worker = UpdateWorker(mode="check")
        self.worker.update_available.connect(self.on_update_available)
        self.worker.no_update.connect(self.on_no_update)
        self.worker.error_occurred.connect(self.on_update_error)
        self.worker.start()

    @Slot(str, str, str)
    def on_update_available(self, new_ver: str, download_url: str, release_notes: str = ""):
        self.download_url = download_url
        self.release_notes = release_notes
        self.status_label.setText(f"Version {new_ver} available!")
        self.status_label.setStyleSheet(
            "color: #2e7d32; font-weight: bold; font-size: 11px;"
        )

        if release_notes:
            self.notes_view.setPlainText(f"Release Notes:\n{release_notes}")
            self.notes_view.show()

        self.update_btn.setText("Download & Install")
        self.update_btn.setEnabled(True)
        self.update_btn.clicked.disconnect()
        self.update_btn.clicked.connect(self.start_download)

    @Slot()
    def on_no_update(self):
        self.status_label.setText(f"App is up to date (v{self.app_version})")
        self.status_label.setStyleSheet("color: #555; font-size: 11px;")
        self.update_btn.setEnabled(True)

    @Slot(str)
    def on_update_error(self, err_msg: str):
        self.status_label.setText("Check failed (Offline or network error)")
        self.status_label.setStyleSheet("color: #c62828; font-size: 11px;")
        self.progress_bar.hide()
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Check for Updates")

    @Slot()
    def start_download(self):
        self.update_btn.setEnabled(False)
        self.status_label.setText("Downloading installer...")
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.worker = UpdateWorker(
            mode="download", download_url=self.download_url
        )
        self.worker.download_progress.connect(self.progress_bar.setValue)
        self.worker.download_finished.connect(self.on_download_complete)
        self.worker.error_occurred.connect(self.on_update_error)
        self.worker.start()

    @Slot(str)
    def on_download_complete(self, installer_path: str):
        self.status_label.setText("Download finished.")
        QMessageBox.information(
            self,
            "Update Ready",
            "The update has finished downloading. Click OK to install.",
            QMessageBox.StandardButton.Ok,
        )
        apply_update_and_exit(installer_path)
