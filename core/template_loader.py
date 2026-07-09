import io
import os
import requests
from pathlib import Path
from openpyxl import load_workbook

# Sheet names inside the template workbook
SHEET_FOAMING   = "Foaming Template"
SHEET_CARPENTER = "Carpenter Template"
SHEET_SALES     = "Sales Summary"

# Drive file ID for the template (same file the old export URL pointed at)
_FILE_ID = "1UZak8H6roTIyS_t09wOoppET-4KtGXPS"

_API_KEY = os.environ.get("GOOGLE_DRIVE_API_KEY", "")

_DRIVE_FILE_URL = f"https://www.googleapis.com/drive/v3/files/{_FILE_ID}"

# On-disk cache of the last-downloaded template, so it survives app restarts
# instead of re-downloading from a cold start every time the app is opened.
_CACHE_DIR  = Path.home() / ".work_order_generator"
_CACHE_FILE = _CACHE_DIR / "template_cache.xlsx"
_HASH_FILE  = _CACHE_DIR / "template_cache.md5"

class TemplateLoader:
    """
    Downloads the template workbook from Google Drive and exposes
    the raw bytes so WorkbookManager can copy sheets from it.

    Before downloading, it asks Drive for the file's md5Checksum 
    and compares it against the hash the on-disk cache was saved 
    with. The full .xlsx is only downloaded when that hash has 
    changed.
    """

    def __init__(self):
        self._bytes: bytes | None = None
        self._checked_this_session = False

    def fetch(self) -> None:
        """
        Check for template changes exactly once per instance. On that
        first call: fetch the remote md5 hash and compare it against the
        hash saved with the disk cache — only download the full workbook
        if they differ. Every later call is a no-op and just keeps using
        what's already in memory.

        Raises ConnectionError if the (first-call) metadata/download
        request fails and there's no usable cache to fall back on.
        Raises KeyError if the resulting bytes are missing expected sheets.
        """
        if self._checked_this_session:
            return

        self._bytes = self._load_current_bytes()
        self._checked_this_session = True
        self._validate_sheets()

    @property
    def raw_bytes(self) -> bytes:
        """Raw .xlsx bytes — passed to WorkbookManager for sheet copying."""
        if self._bytes is None:
            raise RuntimeError("Templates not loaded — call fetch() first.")
        return self._bytes

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _load_current_bytes(self) -> bytes:
        """Cached bytes if the remote hash still matches; otherwise a fresh download."""
        try:
            remote_hash = self._fetch_remote_hash()
        except requests.exceptions.RequestException as e:
            cached = self._read_cache()
            if cached is not None:
                return cached  # offline / API hiccup — fall back to last-known-good copy
            raise ConnectionError(f"Failed to check the Drive template for changes:\n{e}")

        cached_bytes = self._read_cache()
        if cached_bytes is not None and remote_hash == self._read_hash():
            return cached_bytes

        downloaded = self._download()
        self._write_cache(downloaded, remote_hash)
        return downloaded

    @staticmethod
    def _fetch_remote_hash() -> str:
        TemplateLoader._require_api_key()
        response = requests.get(
            _DRIVE_FILE_URL,
            params={"fields": "md5Checksum", "key": _API_KEY},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["md5Checksum"]

    @staticmethod
    def _download() -> bytes:
        TemplateLoader._require_api_key()
        try:
            response = requests.get(
                _DRIVE_FILE_URL,
                params={"alt": "media", "key": _API_KEY},
                timeout=15,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise ConnectionError(
                "Timed out while downloading templates from Google Drive.\n"
                "Check your internet connection and try again."
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to download templates from Google Drive:\n{e}")
        return response.content

    @staticmethod
    def _require_api_key() -> None:
        if not _API_KEY:
            raise RuntimeError(
                "GOOGLE_DRIVE_API_KEY environment variable is not set.\n"
                "Set it to your Drive API key before running the app."
            )

    @staticmethod
    def _read_cache() -> bytes | None:
        """None if there's no cache yet (e.g. very first run on this machine)."""
        try:
            return _CACHE_FILE.read_bytes()
        except FileNotFoundError:
            return None

    @staticmethod
    def _read_hash() -> str | None:
        try:
            return _HASH_FILE.read_text().strip()
        except FileNotFoundError:
            return None

    @staticmethod
    def _write_cache(data: bytes, md5_hash: str) -> None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_bytes(data)
        _HASH_FILE.write_text(md5_hash)

    def _validate_sheets(self) -> None:
        wb = load_workbook(io.BytesIO(self._bytes))
        expected = {SHEET_FOAMING, SHEET_CARPENTER, SHEET_SALES}
        missing  = expected - set(wb.sheetnames)
        if missing:
            raise KeyError(
                f"Template workbook is missing sheets: {', '.join(sorted(missing))}\n"
                f"Expected: {', '.join(sorted(expected))}"
            )