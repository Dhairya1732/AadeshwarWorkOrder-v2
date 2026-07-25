from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFileDialog, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt

from ui.theme import (
    SURFACE, BORDER, BORDER_STR, TEXT_SEC, TEXT_MUTED,
    ACCENT, ACCENT_BG, ACCENT_BDR, GREEN, GREEN_BG, GREEN_BDR, GREEN_TEXT,
)


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

    def reset(self):
        self._path = None
        self._sub.setText("Click to upload")
        self._apply_style(loaded=False)

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

    def reset(self):
        """Revert to the initial (unloaded) state — used when the app resets."""
        self._path = None
        self._icon.setText("↑")
        self._icon.setStyleSheet(f"font-size: 20px; color: {BORDER_STR};")
        self._main_text.setText("Drop CSV here or click to upload")
        self._main_text.setStyleSheet(f"font-size: 13px; color: {TEXT_SEC};")
        self._hint.setText("Pepperfry pending orders export")
        self._hint.setStyleSheet(f"font-size: 11px; color: {BORDER_STR};")
        self._apply_style(loaded=False)

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