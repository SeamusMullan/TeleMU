import json
import sys
from datetime import datetime

import httpx
from PySide6.QtWidgets import (
    QApplication,
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
            "Lovense Resolve LAN": ("POST", "/api/lovense/resolve-lan", '{"token":"","uid":""}'),
            "Lovense Connect": ("POST", "/api/lovense/connect", '{"domain":"","https_port":30010}'),
            "Lovense Get Toys": ("POST", "/api/lovense/get-toys", "{}"),
            "Lovense Function": ("POST", "/api/lovense/function", '{"action":"Vibrate:5","time_sec":2}'),
            "Lovense Stop": ("POST", "/api/lovense/stop", "{}"),
        }

        layout = QVBoxLayout()

        preset_row = QHBoxLayout()
        self.preset_box = QComboBox()
        self.preset_box.addItems(self.presets.keys())
        self.preset_btn = QPushButton("Load Preset")
        self.preset_btn.clicked.connect(self.load_preset)
        preset_row.addWidget(QLabel("Preset"))
        preset_row.addWidget(self.preset_box)
        preset_row.addWidget(self.preset_btn)
        layout.addLayout(preset_row)

        form = QFormLayout()
        self.method = QComboBox()
        self.method.addItems(["GET", "POST"])
        self.path = QLineEdit("/api/health")
        form.addRow("Method", self.method)
        form.addRow("Path", self.path)
        layout.addLayout(form)

        self.body = QPlainTextEdit()
        self.body.setPlaceholderText("JSON body")
        self.body.setMaximumHeight(140)
        layout.addWidget(self.body)

        send_row = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send)
        self.clear_btn = QPushButton("Clear Output")
        self.clear_btn.clicked.connect(self.clear_output)
        send_row.addWidget(self.send_btn)
        send_row.addWidget(self.clear_btn)
        layout.addLayout(send_row)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.setLayout(layout)
        self.load_preset()

    def load_preset(self):
        method, path, body = self.presets[self.preset_box.currentText()]
        self.method.setCurrentText(method)
        self.path.setText(path)
        self.body.setPlainText(body)

    def clear_output(self):
        self.output.clear()

    def send(self):
        method = self.method.currentText()
        path = self.path.text().strip()
        body_text = self.body.toPlainText().strip()
        payload = None
        if method == "POST":
            if body_text:
                try:
                    payload = json.loads(body_text)
                except json.JSONDecodeError as exc:
                    QMessageBox.critical(self, "Invalid JSON", str(exc))
                    return
            else:
                payload = {}
        result = self.sender(method, path, payload)
        self.output.appendPlainText(result)


class LovenseTab(QWidget):
    def __init__(self, sender):
        super().__init__()
        self.sender = sender

        layout = QVBoxLayout()

        form = QGridLayout()
        self.token = QLineEdit()
        self.uid = QLineEdit()
        self.domain = QLineEdit()
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(30010)
        self.action = QLineEdit("Vibrate:5")
        self.time_sec = QSpinBox()
        self.time_sec.setRange(0, 3600)
        self.time_sec.setValue(2)
        self.toy = QLineEdit()

        form.addWidget(QLabel("Token"), 0, 0)
        form.addWidget(self.token, 0, 1)
        form.addWidget(QLabel("UID"), 0, 2)
        form.addWidget(self.uid, 0, 3)
        form.addWidget(QLabel("Domain"), 1, 0)
        form.addWidget(self.domain, 1, 1)
        form.addWidget(QLabel("HTTPS Port"), 1, 2)
        form.addWidget(self.port, 1, 3)
        form.addWidget(QLabel("Action"), 2, 0)
        form.addWidget(self.action, 2, 1)
        form.addWidget(QLabel("Time Sec"), 2, 2)
        form.addWidget(self.time_sec, 2, 3)
        form.addWidget(QLabel("Toy"), 3, 0)
        form.addWidget(self.toy, 3, 1)
        layout.addLayout(form)

        buttons = QGridLayout()
        self.status_btn = QPushButton("Status")
        self.resolve_btn = QPushButton("Resolve LAN")
        self.connect_btn = QPushButton("Connect")
        self.toys_btn = QPushButton("Get Toys")
        self.function_btn = QPushButton("Function")
        self.stop_btn = QPushButton("Stop")
        self.clear_btn = QPushButton("Clear Output")

        self.status_btn.clicked.connect(self.status)
        self.resolve_btn.clicked.connect(self.resolve_lan)
        self.connect_btn.clicked.connect(self.connect_lan)
        self.toys_btn.clicked.connect(self.get_toys)
        self.function_btn.clicked.connect(self.send_function)
        self.stop_btn.clicked.connect(self.stop)
        self.clear_btn.clicked.connect(lambda: self.output.clear())

        buttons.addWidget(self.status_btn, 0, 0)
        buttons.addWidget(self.resolve_btn, 0, 1)
        buttons.addWidget(self.connect_btn, 0, 2)
        buttons.addWidget(self.toys_btn, 1, 0)
        buttons.addWidget(self.function_btn, 1, 1)
        buttons.addWidget(self.stop_btn, 1, 2)
        buttons.addWidget(self.clear_btn, 1, 3)
        layout.addLayout(buttons)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.setLayout(layout)

    def _log(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.output.appendPlainText(f"[{ts}] {text}")

    def status(self):
        self._log(self.sender("GET", "/api/lovense/status", None))

    def resolve_lan(self):
        token = self.token.text().strip()
        uid = self.uid.text().strip()
        if not token or not uid:
            QMessageBox.warning(self, "Missing data", "Token and UID are required.")
            return
        result = self.sender("POST", "/api/lovense/resolve-lan", {"token": token, "uid": uid})
        self._log(result)
        try:
            payload = json.loads(result.split("\n", 1)[1])
        except Exception:
            return
        data = payload.get("data")
        if isinstance(data, dict):
            candidate = data.get("domain") or data.get("wsDomain")
            if isinstance(candidate, str) and candidate:
                self.domain.setText(candidate)
            port = data.get("httpsPort")
            if isinstance(port, int):
                self.port.setValue(port)

    def connect_lan(self):
        domain = self.domain.text().strip()
        if not domain:
            QMessageBox.warning(self, "Missing domain", "Domain is required.")
            return
        self._log(
            self.sender(
                "POST",
                "/api/lovense/connect",
                {"domain": domain, "https_port": self.port.value()},
            )
        )

    def get_toys(self):
        self._log(self.sender("POST", "/api/lovense/get-toys", {}))

    def send_function(self):
        action = self.action.text().strip()
        if not action:
            QMessageBox.warning(self, "Missing action", "Action is required.")
            return
        payload = {
            "action": action,
            "time_sec": self.time_sec.value(),
            "toy": self.toy.text().strip(),
        }
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
        self.resize(1100, 760)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        top = QHBoxLayout()
        top.addWidget(QLabel("Backend Base URL"))
        self.base_url = QLineEdit("http://127.0.0.1:8000")
        self.health_btn = QPushButton("Ping /api/health")
        self.health_btn.clicked.connect(self.ping_health)
        top.addWidget(self.base_url)
        top.addWidget(self.health_btn)
        layout.addLayout(top)

        tabs = QTabWidget()
        tabs.addTab(LovenseTab(self.send_request), "External API (Lovense)")
        tabs.addTab(ApiExplorerTab(self.send_request), "API Explorer")
        layout.addWidget(tabs)

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
