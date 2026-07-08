import io
import requests
from pathlib import Path
from openpyxl import load_workbook

# Sheet names inside the template workbook
SHEET_FOAMING   = "Foaming Template"
SHEET_CARPENTER = "Carpenter Template"
SHEET_SALES     = "Sales Summary"

# Google Sheets export URL — downloads the file as .xlsx without requiring auth
_EXPORT_URL = "https://docs.google.com/spreadsheets/d/1UZak8H6roTIyS_t09wOoppET-4KtGXPS/export?format=xlsx"

# On-disk cache of the last-downloaded template, so it survives app restarts
# instead of re-downloading from a cold start every time the app is opened.
_CACHE_DIR  = Path.home() / ".work_order_generator"
_CACHE_FILE = _CACHE_DIR / "template_cache.xlsx"

class TemplateLoader:
    """
    Downloads the template workbook from Google Drive and exposes
    the raw bytes so WorkbookManager can copy sheets from it.
    The workbook is downloaded once and cached.
    """

    def __init__(self):
        self._bytes: bytes | None = None
        self._checked_this_session = False

    def fetch(self) -> None:
        """
        Check for template changes exactly once per instance. On that
        first call: download the current template, compare it against
        what's cached on disk from a previous session, and overwrite the
        disk cache only if the content actually changed. Every later call
        is a no-op and just keeps using what's already in memory.

        Raises ConnectionError if the (first-call) download fails.
        Raises KeyError if the resulting bytes are missing expected sheets.
        """ 
        if self._checked_this_session:
            return
        
        downloaded = self._download()
        if downloaded != self._read_cache():
            self._write_cache(downloaded)

        self._bytes = downloaded
        self._checked_this_session = True
        self._validate_sheets()

    @property
    def raw_bytes(self) -> bytes:
        """Raw .xlsx bytes — passed to WorkbookManager for sheet copying."""
        if self._bytes is None:
            raise RuntimeError("Templates not loaded — call fetch() first.")
        return self._bytes

    # ── Helpers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _download() -> bytes:
        try:
            response = requests.get(_EXPORT_URL, timeout=15)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise ConnectionError(
                "Timed out while downloading templates from Google Drive.\n"
                "Check your internet connection and try again."
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Failed to download templates from Google Drive:\n{e}"
            )
        return response.content
    
    @staticmethod
    def _read_cache() -> bytes | None:
        """None if there's no cache yet (e.g. very first run on this machine)."""
        try:
            return _CACHE_FILE.read_bytes()
        except FileNotFoundError:
            return None

    @staticmethod
    def _write_cache(data: bytes) -> None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_bytes(data)

    def _validate_sheets(self) -> None:
        wb = load_workbook(io.BytesIO(self._bytes))
        expected = {SHEET_FOAMING, SHEET_CARPENTER, SHEET_SALES}
        missing  = expected - set(wb.sheetnames)
        if missing:
            raise KeyError(
                f"Template workbook is missing sheets: {', '.join(sorted(missing))}\n"
                f"Expected: {', '.join(sorted(expected))}"
            )