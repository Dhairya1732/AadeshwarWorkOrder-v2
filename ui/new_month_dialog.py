from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt

from core.validation import validate_start_number
from models.month_plan import MonthPlan
from ui.theme import BG, SURFACE, BORDER, TEXT, TEXT_SEC, ACCENT
from ui.widgets import FileUploadButton, SectionLabel


class NewMonthDialog(QDialog):
    """
    Shown modally whenever OrderParser encounters orders for a
    workbook_month it hasn't planned for yet (see GenerateWorker._prompt_new_month).
    Blocks the GUI thread until the user picks a starting order no. and,
    optionally, existing Foaming/Carpenter/Sales workbooks to continue —
    the three uploads are all-or-nothing, same as the main window, since
    Pepperfry's three workbooks are always maintained together.

    After exec() returns, self.plan holds the user's answer.
    """

    def __init__(self, month_key: str, parent=None):
        super().__init__(parent)
        self._month_key = month_key
        self.plan: MonthPlan | None = None

        self.setWindowTitle("New month detected")
        self.setMinimumWidth(420)
        # No escaping this without answering — GenerateWorker is blocked
        # waiting on a response, closing the dialog any other way would
        # deadlock it.
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        heading = QLabel(f"Orders found for {self._month_key}")
        heading.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {TEXT};")
        layout.addWidget(heading)

        explainer = QLabel(
            f"There's no workbook set up for {self._month_key} yet. Choose a "
            f"starting order no., and optionally upload existing Foaming, "
            f"Carpenter, and Sales workbooks to continue — leave all three "
            f"blank to start fresh instead."
        )
        explainer.setWordWrap(True)
        explainer.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC};")
        layout.addWidget(explainer)

        layout.addWidget(SectionLabel("Starting order no."))
        self._spin_order_no = QSpinBox()
        self._spin_order_no.setMinimum(1)
        self._spin_order_no.setMaximum(9999)
        self._spin_order_no.setValue(1)
        self._spin_order_no.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        layout.addWidget(self._spin_order_no)

        layout.addWidget(SectionLabel(f"{self._month_key} workbooks (optional)"))
        self._upload_fo = FileUploadButton("Foaming",   "Click to upload")
        self._upload_ca = FileUploadButton("Carpenter", "Click to upload")
        self._upload_so = FileUploadButton("Sales",     "Click to upload")
        layout.addWidget(self._upload_fo)
        layout.addWidget(self._upload_ca)
        layout.addWidget(self._upload_so)

        self._continue_btn = QPushButton("Continue")
        self._continue_btn.setObjectName("continue_btn")
        self._continue_btn.setFixedHeight(34)
        self._continue_btn.clicked.connect(self._on_continue)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._continue_btn)
        layout.addLayout(btn_row)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; }}
            QSpinBox {{
                font-size: 13px;
                height: 34px;
                border: 0.5px solid {BORDER};
                border-radius: 6px;
                background: {SURFACE};
                color: {TEXT};
                padding: 0 10px;
            }}
            QPushButton#continue_btn {{
                font-size: 13px;
                border: none;
                border-radius: 6px;
                background: {ACCENT};
                color: white;
                padding: 0 18px;
                font-weight: 500;
            }}
            QPushButton#continue_btn:hover {{ background: #0C447C; }}
        """)

    # ── Validation / result ─────────────────────────────────────────────────────

    def _on_continue(self):
        uploads = (self._upload_fo, self._upload_ca, self._upload_so)
        loaded_count = sum(u.is_loaded for u in uploads)

        if 0 < loaded_count < 3:
            self._show_error(
                "Upload all three workbooks (Foaming, Carpenter, Sales) to continue "
                "from existing files, or leave all three blank to start fresh."
            )
            return

        foaming_path = self._upload_fo.path if loaded_count == 3 else None
        start_number = self._spin_order_no.value()

        try:
            validate_start_number(foaming_path, start_number)
        except ValueError as e:
            self._show_error(str(e))
            return

        self.plan = MonthPlan(
            start_number   = start_number,
            foaming_path   = foaming_path,
            carpenter_path = self._upload_ca.path if loaded_count == 3 else None,
            sales_path     = self._upload_so.path if loaded_count == 3 else None,
        )
        self.accept()

    def closeEvent(self, event):
        # Escape and Alt+F4 both reach here even with the titlebar close
        # button hidden. GenerateWorker is blocked waiting for self.plan,
        # so this dialog can only close via _on_continue's accept().
        event.ignore()

    def _show_error(self, message: str):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Error")
        dlg.setText(message)
        dlg.setIcon(QMessageBox.Icon.Warning)
        dlg.exec()