import os
import requests
from pathlib import Path

_CACHE_DIR = Path.home() / ".work_order_generator"


class DriveCachedFile:
    """
    Base class for downloading a file from Google Drive, caching it on
    disk, and only re-downloading when Drive reports it has changed.

    Subclasses configure themselves via class attributes:
      _FILE_ID      Drive file ID (required)
      _CHANGE_FIELD Drive metadata field used to detect changes —
                     "md5Checksum" for an ordinary binary file, or
                     "modifiedTime" for a Drive-native doc (Sheets/Docs/
                     Slides don't have a checksum since they aren't
                     stored as a single flat file)
      _CACHE_NAME   filename stem for the on-disk cache, e.g. "template_cache"

    Subclasses only need to override _download() if the file must be
    exported rather than fetched directly (again: Drive-native docs).
    Override _on_loaded() to react once fresh/cached bytes are available
    (e.g. validate contents, parse into a lookup table).
    """

    _API_KEY = os.environ.get("GOOGLE_DRIVE_API_KEY", "")

    _FILE_ID: str
    _CHANGE_FIELD: str = "md5Checksum"
    _CACHE_NAME: str

    def __init__(self):
        self._bytes: bytes | None = None
        self._checked_this_session = False

    def fetch(self) -> None:
        if self._checked_this_session:
            return
        self._bytes = self._load_current_bytes()
        self._checked_this_session = True
        self._on_loaded()

    @property
    def raw_bytes(self) -> bytes:
        if self._bytes is None:
            raise RuntimeError(f"{type(self).__name__} not loaded — call fetch() first.")
        return self._bytes

    # ── Hooks for subclasses ──────────────────────────────────────────────
    def _download(self) -> bytes:
        return self._get(params={"alt": "media", "key": self._API_KEY}, purpose="download").content

    def _on_loaded(self) -> None:
        pass

    # ── Shared plumbing ───────────────────────────────────────────────────
    @property
    def _drive_file_url(self) -> str:
        return f"https://www.googleapis.com/drive/v3/files/{self._FILE_ID}"

    @property
    def _cache_file(self) -> Path:
        return _CACHE_DIR / f"{self._CACHE_NAME}.xlsx"

    @property
    def _meta_file(self) -> Path:
        return _CACHE_DIR / f"{self._CACHE_NAME}.meta"

    def _load_current_bytes(self) -> bytes:
        try:
            remote_token = self._fetch_remote_change_token()
        except requests.exceptions.RequestException as e:
            cached = self._read_cache()
            if cached is not None:
                return cached
            raise ConnectionError(f"Failed to check '{self._CACHE_NAME}' for changes on Drive:\n{e}")

        cached_bytes = self._read_cache()
        if cached_bytes is not None and remote_token == self._read_meta():
            return cached_bytes

        downloaded = self._download()
        self._write_cache(downloaded, remote_token)
        return downloaded

    def _fetch_remote_change_token(self) -> str:
        response = self._get(
            params={"fields": self._CHANGE_FIELD, "key": self._API_KEY},
            purpose="check for changes",
            timeout=10,
        )
        return response.json()[self._CHANGE_FIELD]

    def _get(self, params: dict, purpose: str, timeout: int = 15, url: str | None = None) -> requests.Response:
        self._require_api_key()
        try:
            response = requests.get(url or self._drive_file_url, params=params, timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise ConnectionError(
                f"Timed out while trying to {purpose} from Google Drive.\n"
                "Check your internet connection and try again."
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to {purpose} from Google Drive:\n{e}")
        return response

    def _require_api_key(self) -> None:
        if not self._API_KEY:
            raise RuntimeError(
                "GOOGLE_DRIVE_API_KEY environment variable is not set.\n"
                "Set it to your Drive API key before running the app."
            )

    def _read_cache(self) -> bytes | None:
        try:
            return self._cache_file.read_bytes()
        except FileNotFoundError:
            return None

    def _read_meta(self) -> str | None:
        try:
            return self._meta_file.read_text().strip()
        except FileNotFoundError:
            return None

    def _write_cache(self, data: bytes, token: str) -> None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._cache_file.write_bytes(data)
        self._meta_file.write_text(token)