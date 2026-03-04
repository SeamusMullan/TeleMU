import json
import sys
from datetime import datetime

import httpx
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class ApiExplorerTab(QWidget):
    def __init__(self, sender):
        super().__init__()
        self.sender = sender
        self.presets = {
            "Health": ("GET", "/api/health", ""),
            "List Sessions": ("GET", "/api/sessions", ""),
            "List Tables": ("GET", "/api/tables", ""),
            "Run Query": ("POST", "/api/query", '{"sql":"SELECT 1 as ok"}'),
            "Lovense Status": ("GET", "/api/lovense/status", ""),
            "Lovense Detect Local": ("GET", "/api/lovense/detect-local", ""),
            "Lovense Connect Local": ("POST", "/api/lovense/connect-local", "{}"),
            "Lovense Get Toys": ("POST", "/api/lovense/get-toys", "{}"),
            "Lovense Function": ("POST", "/api/lovense/function", '{"action":"Vibrate:5","time_sec":2}'),
            "Lovense Stop": ("POST", "/api/lovense/stop", "{}"),
        }

        layout = QVBoxLayout()
        row = QHBoxLayout()
        self.preset_box = QComboBox()
        self.preset_box.addItems(self.presets.keys())
        self.load_btn = QPushButton("Load Preset")
        self.load_btn.clicked.connect(self.load_preset)
        row.addWidget(QLabel("Preset"))
        row.addWidget(self.preset_box)
        row.addWidget(self.load_btn)
        layout.addLayout(row)

        form = QFormLayout()
        self.method = QComboBox()
        self.method.addItems(["GET", "POST"])
        self.path = QLineEdit("/api/health")
        form.addRow("Method", self.method)
        form.addRow("Path", self.path)
        layout.addLayout(form)

        self.body = QPlainTextEdit()
        self.body.setPlaceholderText("JSON body")
        self.body.setMaximumHeight(130)
        layout.addWidget(self.body)

        btn_row = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.clear_btn = QPushButton("Clear Output")
        self.send_btn.clicked.connect(self.send)
        btn_row.addWidget(self.send_btn)
        btn_row.addWidget(self.clear_btn)
        layout.addLayout(btn_row)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.clear_btn.clicked.connect(self.output.clear)
        layout.addWidget(self.output)
        self.setLayout(layout)
        self.load_preset()

    def load_preset(self):
        method, path, body = self.presets[self.preset_box.currentText()]
        self.method.setCurrentText(method)
        self.path.setText(path)
        self.body.setPlainText(body)

    def send(self):
        method = self.method.currentText()
        path = self.path.text().strip()
        payload = None
        if method == "POST":
            raw = self.body.toPlainText().strip()
            if raw:
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError as exc:
                    QMessageBox.critical(self, "Invalid JSON", str(exc))
                    return
            else:
                payload = {}
        self.output.appendPlainText(self.sender(method, path, payload))


class LovenseTab(QWidget):
    def __init__(self, sender, settings: QSettings):
        super().__init__()
        self.sender = sender
        self.settings = settings

        layout = QVBoxLayout()
        form = QGridLayout()
        self.domain = QLineEdit(str(self.settings.value("lovense/domain", "")))
        self.domain.setReadOnly(True)
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(int(self.settings.value("lovense/https_port", 30010)))
        self.action = QLineEdit("Vibrate:5")
        self.time_sec = QSpinBox()
        self.time_sec.setRange(0, 3600)
        self.time_sec.setValue(2)
        self.toy = QLineEdit()
        self.auto_connect_startup = QCheckBox("Auto-connect on startup")
        self.auto_connect_startup.setChecked(
            str(self.settings.value("lovense/auto_connect_startup", "true")).lower() == "true"
        )

        form.addWidget(QLabel("Detected Domain"), 0, 0)
        form.addWidget(self.domain, 0, 1)
        form.addWidget(QLabel("HTTPS Port"), 0, 2)
        form.addWidget(self.port, 0, 3)
        form.addWidget(QLabel("Action"), 1, 0)
        form.addWidget(self.action, 1, 1)
        form.addWidget(QLabel("Time Sec"), 1, 2)
        form.addWidget(self.time_sec, 1, 3)
        form.addWidget(QLabel("Toy"), 2, 0)
        form.addWidget(self.toy, 2, 1)
        form.addWidget(self.auto_connect_startup, 2, 2, 1, 2)
        layout.addLayout(form)

        buttons = QGridLayout()
        self.status_btn = QPushButton("Status")
        self.detect_btn = QPushButton("Detect Local App")
        self.local_btn = QPushButton("Local Connect")
        self.toys_btn = QPushButton("Get Toys")
        self.function_btn = QPushButton("Function")
        self.stop_btn = QPushButton("Stop")
        self.clear_btn = QPushButton("Clear Output")

        self.status_btn.clicked.connect(self.status)
        self.detect_btn.clicked.connect(self.detect_local)
        self.local_btn.clicked.connect(self.local_connect)
        self.toys_btn.clicked.connect(self.get_toys)
        self.function_btn.clicked.connect(self.send_function)
        self.stop_btn.clicked.connect(self.stop)
        self.clear_btn.clicked.connect(self.clear_output)
        self.auto_connect_startup.stateChanged.connect(self.save_settings)

        buttons.addWidget(self.status_btn, 0, 0)
        buttons.addWidget(self.detect_btn, 0, 1)
        buttons.addWidget(self.local_btn, 0, 2)
        buttons.addWidget(self.toys_btn, 0, 3)
        buttons.addWidget(self.function_btn, 1, 2)
        buttons.addWidget(self.stop_btn, 1, 3)
        buttons.addWidget(self.clear_btn, 2, 3)
        layout.addLayout(buttons)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def _log(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.output.appendPlainText(f"[{ts}] {text}")

    def _parse(self, response_text):
        try:
            header, body = response_text.split("\n", 1)
            status = int(header.rsplit("->", 1)[1].strip())
            payload = json.loads(body)
            return status, payload
        except Exception:
            return None, None

    def save_settings(self):
        self.settings.setValue("lovense/domain", self.domain.text().strip())
        self.settings.setValue("lovense/https_port", self.port.value())
        self.settings.setValue(
            "lovense/auto_connect_startup",
            "true" if self.auto_connect_startup.isChecked() else "false",
        )

    def clear_output(self):
        self.output.clear()

    def status(self):
        self._log(self.sender("GET", "/api/lovense/status", None))

    def detect_local(self):
        result = self.sender("GET", "/api/lovense/detect-local", None)
        self._log(result)
        status, payload = self._parse(result)
        if status is None or status >= 400 or not isinstance(payload, dict):
            return False
        domain = payload.get("domain")
        https_port = payload.get("https_port")
        if isinstance(domain, str) and domain.strip():
            self.domain.setText(domain.strip())
        if isinstance(https_port, int):
            self.port.setValue(https_port)
        self.save_settings()
        return bool(self.domain.text().strip())

    def local_connect(self):
        result = self.sender("POST", "/api/lovense/connect-local", {})
        self._log(result)
        status, payload = self._parse(result)
        if status is None or status >= 400:
            return False
        if isinstance(payload, dict):
            domain = payload.get("domain")
            https_port = payload.get("https_port")
            if isinstance(domain, str) and domain.strip():
                self.domain.setText(domain.strip())
            if isinstance(https_port, int):
                self.port.setValue(https_port)
        self.save_settings()
        return True

    def get_toys(self):
        self._log(self.sender("POST", "/api/lovense/get-toys", {}))

    def send_function(self):
        action = self.action.text().strip()
        if not action:
            QMessageBox.warning(self, "Missing action", "Action is required.")
            return
        payload = {"action": action, "time_sec": self.time_sec.value(), "toy": self.toy.text().strip()}
        self._log(self.sender("POST", "/api/lovense/function", payload))

    def stop(self):
        toy = self.toy.text().strip()
        path = "/api/lovense/stop"
        if toy:
            path = f"/api/lovense/stop?toy={toy}"
        self._log(self.sender("POST", path, {}))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TeleMU Backend Test UI")
        self.resize(1080, 760)
        self.settings = QSettings("TeleMU", "BackendTestUI")

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        top = QHBoxLayout()
        top.addWidget(QLabel("Backend Base URL"))
        self.base_url = QLineEdit(str(self.settings.value("backend/base_url", "http://127.0.0.1:8000")))
        self.health_btn = QPushButton("Ping /api/health")
        self.health_btn.clicked.connect(self.ping_health)
        self.base_url.editingFinished.connect(self.save_settings)
        top.addWidget(self.base_url)
        top.addWidget(self.health_btn)
        layout.addLayout(top)

        tabs = QTabWidget()
        self.lovense_tab = LovenseTab(self.send_request, self.settings)
        tabs.addTab(self.lovense_tab, "External API (Lovense Local)")
        tabs.addTab(ApiExplorerTab(self.send_request), "API Explorer")
        layout.addWidget(tabs)
        QTimer.singleShot(300, self.auto_connect_on_startup)

    def save_settings(self):
        self.settings.setValue("backend/base_url", self.base_url.text().strip())

    def auto_connect_on_startup(self):
        if self.lovense_tab.auto_connect_startup.isChecked():
            self.lovense_tab.local_connect()

    def send_request(self, method, path, payload):
        base = self.base_url.text().strip().rstrip("/")
        path = path.strip()
        if not path.startswith("/"):
            path = "/" + path
        url = f"{base}{path}"
        try:
            with httpx.Client(timeout=10.0) as client:
                if method == "GET":
                    resp = client.get(url)
                else:
                    resp = client.post(url, json=payload)
            try:
                body = json.dumps(resp.json(), indent=2)
            except Exception:
                body = resp.text
            return f"{method} {path} -> {resp.status_code}\n{body}\n"
        except Exception as exc:
            return f"{method} {path} -> ERROR\n{exc}\n"

    def ping_health(self):
        QMessageBox.information(self, "Health", self.send_request("GET", "/api/health", None))


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
