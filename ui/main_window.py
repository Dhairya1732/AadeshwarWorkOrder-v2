from PyQt6.QtWidgets import (
    QLayout, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox,
    QFileDialog, QFrame, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt

from ui.worker import GenerateWorker


# ── Colour palette ─────────────────────────────────────────────────────────────
BG          = "#f5f4f0"
SURFACE     = "#ffffff"
BORDER      = "#d3d1c7"
BORDER_STR  = "#b4b2a9"
TEXT        = "#2c2c2a"
TEXT_SEC    = "#5F5E5A"
TEXT_MUTED  = "#888780"
ACCENT      = "#185FA5"
ACCENT_BG   = "#E6F1FB"
ACCENT_BDR  = "#85B7EB"
GREEN       = "#639922"
GREEN_BG    = "#EAF3DE"
GREEN_BDR   = "#97C459"
GREEN_TEXT  = "#27500A"
ORANGE      = "#EF9F27"
RED         = "#C0392B"


# ── Reusable styled widgets ─────────────────────────────────────────────────────

class SectionLabel(QLabel):
    """Small all-caps muted label used above each section."""
    def __init__(self, text: str):
        super().__init__(text.upper())
        self.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 500; letter-spacing: 0.05em;")


class Divider(QFrame):
    """Horizontal rule."""
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"color: {BORDER};")
        self.setFixedHeight(1)


class FileUploadButton(QWidget):
    """
    A toggleable pill that shows an active sheet's name and type.
    Starts in the loaded (green) state.
    """
    def __init__(self, label: str, sub: str):
        super().__init__()
        self._path: str | None = None
        self.setMaximumWidth(500)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(11, 8, 11, 8)
        layout.setSpacing(8)

        self._icon = QLabel("▦")
        self._icon.setFixedWidth(16)

        self._label = QLabel(label)
        self._label.setStyleSheet("font-size: 12px; font-weight: 500;")

        self._sub = QLabel(sub)
        self._sub.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._sub.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout.addWidget(self._icon)
        layout.addWidget(self._label)
        layout.addWidget(self._sub)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._apply_style(loaded=False)

    def _apply_style(self, loaded: bool):
        if loaded:
            self.setStyleSheet(f"""
                FileUploadButton {{
                    border: 0.5px solid {GREEN_BDR};
                    border-radius: 6px;
                    background: {GREEN_BG};
                }}
            """)
            self._icon.setStyleSheet(f"color: {GREEN_TEXT};")
            self._label.setStyleSheet(f"color: {GREEN_TEXT};")
            self._sub.setStyleSheet(f"color: {GREEN};")
        else:
            self.setStyleSheet(f"""
                FileUploadButton {{
                    border: 0.5px solid {BORDER};
                    border-radius: 6px;
                    background: {SURFACE};
                }}
            """)
            self._icon.setStyleSheet(f"color: {BORDER_STR};")
            self._label.setStyleSheet(f"color: {TEXT_SEC};")
            self._sub.setStyleSheet(f"color: {BORDER_STR};")

    def set_enabled_interaction(self, enabled: bool):
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled
            else Qt.CursorShape.ForbiddenCursor
        )
        self._can_toggle = enabled

    def mousePressEvent(self, event):
        if not getattr(self, "_can_toggle", True):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select {self._label.text()} template", "", "Excel Files (*.xlsx)"
        )
        if path:
            self._path = path
            self._load(path)
        
    def _load(self, path: str):
        filename = path.split("/")[-1].split("\\")[-1]
        self._sub.setText(filename)
        self._apply_style(loaded=True)

    @property
    def path(self) -> str | None:
        return self._path

    @property
    def is_loaded(self) -> bool:
        return self._path is not None


class CsvUploadButton(QWidget):
    """
    Dashed drop-zone for the pending orders CSV.
    Clicking opens a file dialog. Shows filename + row count once loaded.
    """
    def __init__(self):
        super().__init__()
        self._path: str | None = None
        self.setFixedSize(240, 110)

        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon  = QLabel("↑")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet(f"font-size: 20px; color: {BORDER_STR};")

        self._main_text = QLabel("Drop CSV here or click to upload")
        self._main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_text.setStyleSheet(f"font-size: 13px; color: {TEXT_SEC};")

        self._hint = QLabel("Pepperfry pending orders export")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet(f"font-size: 11px; color: {BORDER_STR};")

        self._layout.addWidget(self._icon)
        self._layout.addWidget(self._main_text)
        self._layout.addWidget(self._hint)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._apply_style(loaded=False)

    def _apply_style(self, loaded: bool):
        if loaded:
            self.setStyleSheet(f"""
                CsvUploadButton {{
                    border: 0.5px solid {ACCENT_BDR};
                    border-radius: 8px;
                    background: {ACCENT_BG};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                CsvUploadButton {{
                    border: 1px solid {BORDER_STR};
                    border-radius: 8px;
                    background: {SURFACE};
                }}
            """)

    def mousePressEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select pending orders CSV", "", "CSV Files (*.csv)"
        )
        if path:
            self._path = path
            self._load(path)

    def _load(self, path: str):
        import pandas as pd
        try:
            df = pd.read_csv(path)
            row_count = len(df)
        except Exception:
            row_count = "?"

        filename = path.split("/")[-1].split("\\")[-1]
        self._icon.setText("✓")
        self._icon.setStyleSheet(f"font-size: 20px; color: {ACCENT};")
        self._main_text.setText(filename)
        self._main_text.setStyleSheet(f"font-size: 13px; color: {ACCENT}; font-weight: 500;")
        self._hint.setText(f"{row_count} orders · click to replace")
        self._hint.setStyleSheet(f"font-size: 11px; color: {ACCENT}; opacity: 0.8;")
        self._apply_style(loaded=True)

    @property
    def path(self) -> str | None:
        return self._path

    @property
    def is_loaded(self) -> bool:
        return self._path is not None


class ProgressBar(QWidget):
    """A labelled progress bar with a sub-label for status text."""
    def __init__(self, label: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        header = QHBoxLayout()
        self._label = QLabel(label)
        self._label.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {TEXT_SEC};")
        self._pct = QLabel("0%")
        self._pct.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        header.addWidget(self._label)
        header.addWidget(self._pct)

        # Track bar (manual, since QProgressBar is hard to style finely)
        self._track = QFrame()
        self._track.setFixedHeight(5)
        self._track.setStyleSheet(f"background: #e3e2dd; border-radius: 3px;")

        self._fill = QFrame(self._track)
        self._fill.setFixedHeight(5)
        self._fill.setStyleSheet(f"background: {ACCENT}; border-radius: 3px;")
        self._fill.setFixedWidth(0)

        self._sub = QLabel("Waiting…")
        self._sub.setStyleSheet(f"font-size: 11px; color: {BORDER_STR};")

        layout.addLayout(header)
        layout.addWidget(self._track)
        layout.addWidget(self._sub)

    def set_value(self, pct: int):
        pct = max(0, min(100, pct))
        self._pct.setText(f"{pct}%")
        track_w = self._track.width()
        self._fill.setFixedWidth(int(track_w * pct / 100))

    def set_sub(self, text: str, state: str = "waiting"):
        # state: "waiting" | "active" | "done"
        colour = {
            "waiting": BORDER_STR,
            "active":  TEXT_MUTED,
            "done":    ACCENT,
        }.get(state, BORDER_STR)
        self._sub.setText(text)
        self._sub.setStyleSheet(f"font-size: 11px; color: {colour};")

    def resizeEvent(self, event):
        # Keep fill width correct when window is resized
        super().resizeEvent(event)
        pct_text = self._pct.text().replace("%", "")
        try:
            pct = int(pct_text)
        except ValueError:
            pct = 0
        self._fill.setFixedWidth(int(self._track.width() * pct / 100))

    @property
    def value(self) -> int:
        return int(self._pct.text().replace("%", "") or 0)


# ── Main window ─────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Work Order Generator")
        self.setMinimumWidth(640)

        # self._worker: GenerateWorker | None = None

        self._build_ui()
        self._apply_global_style()

    # ── UI construction ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        outer.addLayout(self._build_inputs_row())
        outer.addWidget(self._build_params_card())
        outer.addWidget(Divider())
        outer.addLayout(self._build_actions_row())
        outer.addLayout(self._build_progress_section())
        outer.addStretch()

    def _build_inputs_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(16)

        # Left: CSV upload
        left = QVBoxLayout()
        left.setSpacing(7)
        left.addWidget(SectionLabel("Pending orders"))
        self._csv_upload_button = CsvUploadButton()
        left.addWidget(self._csv_upload_button)
        left.setAlignment(Qt.AlignmentFlag.AlignTop)
        left.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        # Right: active sheets
        right = QVBoxLayout()
        right.setSpacing(7)
        right.addWidget(SectionLabel("Active sheets"))
        self._upload_fo = FileUploadButton("Foaming",   "Click to upload")
        self._upload_ca = FileUploadButton("Carpenter", "Click to upload")
        self._upload_so = FileUploadButton("Sales",     "Click to upload")
        right.addWidget(self._upload_fo)
        right.addWidget(self._upload_ca)
        right.addWidget(self._upload_so)
        right.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addLayout(left)
        layout.addLayout(right)
        return layout

    def _build_params_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("card")
        card.setMaximumWidth(300)
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(16)

        # Starting order number
        left = QVBoxLayout()
        left.setSpacing(5)
        left.addWidget(QLabel("Starting order no."))
        self._spin_order_no = QSpinBox()
        self._spin_order_no.setMinimum(1)
        self._spin_order_no.setMaximum(9999)
        self._spin_order_no.setValue(1)
        self._spin_order_no.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        left.addWidget(self._spin_order_no)

        row.addLayout(left)
        return card

    def _build_actions_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        # Status indicator
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(f"color: {GREEN}; font-size: 9px;")
        self._status_text = QLabel("Ready")
        self._status_text.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED};")

        status_row = QHBoxLayout()
        status_row.setSpacing(7)
        status_row.addWidget(self._status_dot)
        status_row.addWidget(self._status_text)
        status_row.addStretch()

        # Generate button
        self._gen_btn = QPushButton("Generate")
        self._gen_btn.setObjectName("gen_btn")
        self._gen_btn.setFixedHeight(34)
        self._gen_btn.setMinimumWidth(110)
        self._gen_btn.clicked.connect(self._on_generate)

        layout.addLayout(status_row)
        layout.addWidget(self._gen_btn)
        return layout

    def _build_progress_section(self) -> QVBoxLayout:
        self._progress_section = QVBoxLayout()
        self._progress_section.setSpacing(14)

        self._bar_fo = ProgressBar("Foaming sheets")
        self._bar_ca = ProgressBar("Carpenter sheets")
        self._bar_so = ProgressBar("Sales summaries")

        # Overall bar
        overall_widget = QWidget()
        overall_layout = QVBoxLayout(overall_widget)
        overall_layout.setContentsMargins(0, 4, 0, 0)
        overall_layout.setSpacing(5)
        overall_widget.setStyleSheet(f"border-top: 0.5px solid {BORDER};")

        overall_header = QHBoxLayout()
        overall_lbl = QLabel("Overall")
        overall_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED};")
        self._overall_pct = QLabel("0%")
        self._overall_pct.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self._overall_pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        overall_header.addWidget(overall_lbl)
        overall_header.addWidget(self._overall_pct)

        self._overall_track = QFrame()
        self._overall_track.setFixedHeight(3)
        self._overall_track.setStyleSheet(f"background: #e3e2dd; border-radius: 2px;")
        self._overall_fill = QFrame(self._overall_track)
        self._overall_fill.setFixedHeight(3)
        self._overall_fill.setStyleSheet(f"background: {ACCENT}; border-radius: 2px;")
        self._overall_fill.setFixedWidth(0)

        overall_layout.addLayout(overall_header)
        overall_layout.addWidget(self._overall_track)

        # Hidden by default — shown once generation starts
        self._bar_fo.hide()
        self._bar_ca.hide()
        self._bar_so.hide()
        overall_widget.hide()
        self._overall_widget = overall_widget

        self._progress_section.addWidget(self._bar_fo)
        self._progress_section.addWidget(self._bar_ca)
        self._progress_section.addWidget(self._bar_so)
        self._progress_section.addWidget(overall_widget)

        return self._progress_section

    # ── Styling ─────────────────────────────────────────────────────────────────

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget#root {{
                background: {BG};
            }}
            QWidget#card {{
                background: {SURFACE};
                border: 0.5px solid {BORDER};
                border-radius: 10px;
            }}
            QLabel {{
                color: {TEXT_SEC};
                font-size: 13px;
                background: transparent;
                border: none;
            }}
            QSpinBox {{
                font-size: 13px;
                height: 34px;
                border: 0.5px solid {BORDER};
                border-radius: 6px;
                background: {SURFACE};
                color: {TEXT};
                padding: 0 10px;
            }}
            QSpinBox:focus {{
                border-color: {ACCENT};
            }}
            QPushButton#gen_btn {{
                font-size: 13px;
                height: 34px;
                border: none;
                border-radius: 6px;
                background: {ACCENT};
                color: white;
                padding: 0 16px;
                font-weight: 500;
            }}
            QPushButton#gen_btn:hover {{
                background: #0C447C;
            }}
            QPushButton#gen_btn:disabled {{
                background: {BORDER};
                color: {TEXT_MUTED};
            }}
        """)

    # ── Slots ───────────────────────────────────────────────────────────────────

    def _on_generate(self):
        # ── Validate inputs ──
        if not self._upload_fo.is_loaded:
            self._show_error("Please upload the foaming sheet before generating.")
            return
        
        if not self._upload_ca.is_loaded:
            self._show_error("Please upload the carpenter sheet before generating.")
            return
        
        if not self._upload_so.is_loaded:
            self._show_error("Please upload the sales sheet before generating.")
            return
        
        if not self._csv_upload_button.is_loaded:
            self._show_error("Please upload a pending orders CSV before generating.")
            return

        # ── Lock UI ──
        self._gen_btn.setEnabled(False)
        self._set_status("running", "Generating…")
        self._lock_inputs(True)

        # ── Show progress bars ──
        self._bar_fo.show()
        self._bar_ca.show()
        self._bar_so.show()
        self._overall_widget.show()
        self._reset_bars()

        # ── Spin up worker ──
        self._worker = GenerateWorker(
            csv_path      = self._csv_upload_button.path,
            foaming_path  = self._upload_fo.path,
            carpenter_path= self._upload_ca.path,
            sales_path    = self._upload_so.path,
            start_number  = self._spin_order_no.value(),
        )
        self._worker.foaming_progress.connect(self._on_fo_progress)
        self._worker.carpenter_progress.connect(self._on_ca_progress)
        self._worker.sales_progress.connect(self._on_so_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_fo_progress(self, pct: int, msg: str):
        self._bar_fo.set_value(pct)
        self._bar_fo.set_sub(msg, "active" if pct < 100 else "done")
        self._update_overall()

    def _on_ca_progress(self, pct: int, msg: str):
        self._bar_ca.set_value(pct)
        self._bar_ca.set_sub(msg, "active" if pct < 100 else "done")
        self._update_overall()

    def _on_so_progress(self, pct: int, msg: str):
        self._bar_so.set_value(pct)
        self._bar_so.set_sub(msg, "active" if pct < 100 else "done")
        self._update_overall()

    def _update_overall(self):
        fo = self._bar_fo.value
        ca = self._bar_ca.value
        so = self._bar_so.value
        avg = (fo + ca + so) // 3
        self._overall_pct.setText(f"{avg}%")
        track_w = self._overall_track.width()
        self._overall_fill.setFixedWidth(int(track_w * avg / 100))

    def _on_done(self, files_written: int):
        self._set_status("done", f"Done · {files_written} files saved")
        self._gen_btn.setEnabled(True)
        self._gen_btn.setText("↺  New batch")
        self._lock_inputs(False)

    def _on_error(self, message: str):
        self._set_status("error", "Error — see details")
        self._gen_btn.setEnabled(True)
        self._lock_inputs(False)
        self._show_error(f"Generation failed:\n\n{message}")

    # ── Helpers ──────────────────────────────────────────────────────────────────

    def _set_status(self, state: str, text: str):
        colours = {
            "ready":   GREEN,
            "running": ORANGE,
            "done":    GREEN,
            "error":   RED,
        }
        self._status_dot.setStyleSheet(f"color: {colours.get(state, BORDER_STR)}; font-size: 9px;")
        self._status_text.setText(text)

    def _lock_inputs(self, locked: bool):
        self._csv_upload_button.setEnabled(not locked)
        self._spin_order_no.setEnabled(not locked)
        for file in (self._upload_fo, self._upload_ca, self._upload_so):
            file.set_enabled_interaction(not locked)

    def _reset_bars(self):
        for bar in (self._bar_fo, self._bar_ca, self._bar_so):
            bar.set_value(0)
            bar.set_sub("Waiting…", "waiting")
        self._overall_pct.setText("0%")
        self._overall_fill.setFixedWidth(0)

    def _show_error(self, message: str):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Error")
        dlg.setText(message)
        dlg.setIcon(QMessageBox.Icon.Warning)
        dlg.exec()