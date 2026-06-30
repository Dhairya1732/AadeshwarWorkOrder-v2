import io
import requests
from openpyxl import load_workbook

# Sheet names inside the template workbook
SHEET_FOAMING   = "Foaming Template"
SHEET_CARPENTER = "Carpenter Template"
SHEET_SALES     = "Sales Summary"

# Google Sheets export URL — downloads the file as .xlsx without requiring auth
_EXPORT_URL = "https://docs.google.com/spreadsheets/d/1UZak8H6roTIyS_t09wOoppET-4KtGXPS/export?format=xlsx"


class TemplateLoader:
    """
    Downloads the template workbook from Google Drive and exposes
    the raw bytes so WorkbookManager can copy sheets from it.
    The workbook is downloaded once and cached.
    """

    def __init__(self):
        self._bytes: bytes | None = None

    def fetch(self) -> None:
        """
        Download the template workbook from Google Drive and cache the raw bytes.
        Raises ConnectionError if the download fails.
        Raises KeyError if any expected sheet is missing.
        """
        
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

        self._bytes = response.content
        self._validate_sheets()

    @property
    def raw_bytes(self) -> bytes:
        """Raw .xlsx bytes — passed to WorkbookManager for sheet copying."""
        if self._bytes is None:
            raise RuntimeError("Templates not loaded — call fetch() first.")
        return self._bytes

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _validate_sheets(self) -> None:
        wb = load_workbook(io.BytesIO(self._bytes))
        expected = {SHEET_FOAMING, SHEET_CARPENTER, SHEET_SALES}
        missing  = expected - set(wb.sheetnames)
        if missing:
            raise KeyError(
                f"Template workbook is missing sheets: {', '.join(sorted(missing))}\n"
                f"Expected: {', '.join(sorted(expected))}"
            )