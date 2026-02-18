"""
telegram_notifier.py
Auto-load .env on every send. Single chat. Python 3.10+.

Features
- Auto-reads .env / env on each API call (no manual load needed)
- Single destination chat (normal + monitoring)
- send_message / send_photo / send_document / send_media_group
- Retry with exponential backoff (handles 429 Retry-After)
- Exceptions: TelegramNetworkError / TelegramHTTPError / TelegramAPIError
- Monitoring: notify_error(), @monitor_exceptions
- Global hooks: install_global_handlers() for uncaught exceptions & ERROR logs

ENV keys (read every call)
- TELEGRAM_BOT_TOKEN            (required)
- TELEGRAM_DEFAULT_CHAT_ID      (recommended; else pass chat_id)
- TELEGRAM_PROXY                (optional, http/https proxy)
- TELEGRAM_TIMEOUT              (optional, int, default 15)
- TELEGRAM_MAX_RETRIES          (optional, int, default 4)
- TELEGRAM_BACKOFF_FACTOR       (optional, float, default 0.75)
- TELEGRAM_BASE_URL             (optional, default https://api.telegram.org)
"""
from __future__ import annotations

import json
import logging
import os
import time
import traceback
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple, List

import requests

try:
    # optional; if present, we'll call it each time to refresh env from .env
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # pragma: no cover


# -----------------------
# Exceptions
# -----------------------
class TelegramNotifierError(Exception):
    """Base exception for the telegram_notifier module."""


class TelegramNetworkError(TelegramNotifierError):
    """Raised for network/connection issues (DNS/TLS/timeout)."""


class TelegramHTTPError(TelegramNotifierError):
    """Raised for non-200 HTTP responses from Telegram edge."""

    def __init__(self, status_code: int, text: str):
        super().__init__(f"HTTP {status_code}: {text[:200]}")
        self.status_code = status_code
        self.text = text


class TelegramAPIError(TelegramNotifierError):
    """Raised when Telegram returns ok=False."""

    def __init__(self, error_code: int, description: str, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(f"API {error_code}: {description}")
        self.error_code = error_code
        self.description = description
        self.parameters = parameters or {}


# -----------------------
# Runtime snapshot (filled per call)
# -----------------------
@dataclass
class _Runtime:
    token: str
    chat_id: Optional[str]
    base_url: str
    timeout: int
    max_retries: int
    backoff_factor: float
    proxy: Optional[str]


# -----------------------
# Main class
# -----------------------
class TelegramNotifier:
    """High-level wrapper over Telegram Bot API with retries and auto .env loading."""

    MAX_MESSAGE_LEN = 4096

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "telegram-notifier/1.3"})
        self.log = logging.getLogger(self.__class__.__name__)

    # --------- Public API ---------
    def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a text message (auto-chunk > 4096). Returns last JSON result."""
        rt = self._runtime()
        target = chat_id or rt.chat_id
        if not target:
            raise ValueError("chat_id is required (no TELEGRAM_DEFAULT_CHAT_ID)")

        results: Dict[str, Any] = {}
        for part in self._chunk_text(text, self.MAX_MESSAGE_LEN):
            payload: Dict[str, Any] = {"chat_id": target, "text": part}
            if parse_mode is not None:
                payload["parse_mode"] = parse_mode
            if disable_web_page_preview is not None:
                payload["disable_web_page_preview"] = disable_web_page_preview
            if protect_content is not None:
                payload["protect_content"] = protect_content
            if reply_to_message_id is not None:
                payload["reply_to_message_id"] = reply_to_message_id
            if message_thread_id is not None:
                payload["message_thread_id"] = message_thread_id
            if reply_markup is not None:
                payload["reply_markup"] = json.dumps(reply_markup)

            results = self._call(rt, "sendMessage", data=payload)
        return results

    def send_photo(
        self,
        photo: Tuple[str, bytes] | str,
        caption: Optional[str] = None,
        chat_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a photo with optional caption. photo: (filename, bytes) or str file_id/URL."""
        rt = self._runtime()
        target = chat_id or rt.chat_id
        if not target:
            raise ValueError("chat_id is required (no TELEGRAM_DEFAULT_CHAT_ID)")

        data: Dict[str, Any] = {"chat_id": target}
        if caption:
            data["caption"] = caption[: self.MAX_MESSAGE_LEN]
        if parse_mode:
            data["parse_mode"] = parse_mode
        if message_thread_id is not None:
            data["message_thread_id"] = message_thread_id
        if reply_markup is not None:
            data["reply_markup"] = json.dumps(reply_markup)

        files = None
        if isinstance(photo, tuple):
            files = {"photo": photo}
        else:
            data["photo"] = photo

        return self._call(rt, "sendPhoto", data=data, files=files)

    def send_document(
        self,
        document: Tuple[str, bytes] | str,
        caption: Optional[str] = None,
        chat_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a document (CSV/PDF/ZIP...). document: (filename, bytes) or str file_id/URL."""
        rt = self._runtime()
        target = chat_id or rt.chat_id
        if not target:
            raise ValueError("chat_id is required (no TELEGRAM_DEFAULT_CHAT_ID)")

        data: Dict[str, Any] = {"chat_id": target}
        if caption:
            data["caption"] = caption[: self.MAX_MESSAGE_LEN]
        if parse_mode:
            data["parse_mode"] = parse_mode
        if message_thread_id is not None:
            data["message_thread_id"] = message_thread_id
        if reply_markup is not None:
            data["reply_markup"] = json.dumps(reply_markup)

        files = None
        if isinstance(document, tuple):
            files = {"document": document}
        else:
            data["document"] = document

        return self._call(rt, "sendDocument", data=data, files=files)

    def send_media_group(
        self,
        medias: List[Dict[str, Any]],
        chat_id: Optional[str] = None,
        message_thread_id: Optional[int] = None,
        disable_notification: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send an album (media group) of photos/videos. Up to 10 items.

        medias: list like:
          {"type": "photo", "media": "file_id_or_url", "caption": "...", "parse_mode": "Markdown"}
          or with upload bytes: {"type": "photo", "media": ("photo1.jpg", b"...")}
        """
        rt = self._runtime()
        target = chat_id or rt.chat_id
        if not target:
            raise ValueError("chat_id is required (no TELEGRAM_DEFAULT_CHAT_ID)")

        files: Dict[str, Tuple[str, bytes]] = {}
        media_payload: List[Dict[str, Any]] = []
        file_index = 0
        for item in medias:
            it = dict(item)
            media = it.get("media")
            if isinstance(media, tuple) and len(media) == 2 and isinstance(media[0], str) and isinstance(media[1], (bytes, bytearray)):
                attach_name = f"file{file_index}"
                files[attach_name] = (media[0], media[1])
                it["media"] = f"attach://{attach_name}"
                file_index += 1
            media_payload.append(it)

        data: Dict[str, Any] = {"chat_id": target, "media": json.dumps(media_payload)}
        if message_thread_id is not None:
            data["message_thread_id"] = message_thread_id
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id

        return self._call(rt, "sendMediaGroup", data=data, files=files or None)

    # --------- Monitoring helpers ---------
    def notify_error(self, err: BaseException, context: Optional[str] = None) -> None:
        """Send a Persian monitoring message to default chat (best-effort)."""
        try:
            title = "🚨 خطای سیستم"
            ctx = f"\n\n🧩 زمینه: {context}" if context else ""
            tb = self._format_trace(err)
            body = f"{title}{ctx}\n\n```\n{tb}\n```"
            self.send_message(body, parse_mode="Markdown")
        except Exception as monitor_err:  # pragma: no cover
            self.log.error("Failed to send monitoring error: %s", monitor_err)

    def monitor_exceptions(self, context: Optional[str] = None):
        """Decorator to auto-notify chat when the wrapped function raises."""
        def _decorator(func):
            def _wrapped(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # noqa: BLE001
                    self.notify_error(e, context=context or func.__name__)
                    raise
            return _wrapped
        return _decorator

    # --------- Internal HTTP plumbing ---------
    def _call(
        self,
        rt: _Runtime,
        method: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform a Telegram API call with retries and backoff."""
        url = f"{rt.base_url}/bot{rt.token}/{method}"
        # Apply proxy per-call in case it changed in env:
        if rt.proxy:
            self.session.proxies.update({"http": rt.proxy, "https": rt.proxy})
        else:
            self.session.proxies.clear()

        attempt = 0
        while True:
            try:
                if files:
                    resp = self.session.post(url, data=data or {}, files=files, timeout=rt.timeout)
                else:
                    resp = self.session.post(url, data=data or {}, timeout=rt.timeout)
            except requests.RequestException as e:
                self._maybe_sleep(rt, attempt, retry_after=None)
                if attempt >= rt.max_retries:
                    raise TelegramNetworkError(str(e)) from e
                attempt += 1
                continue

            if resp.status_code != 200:
                retry_after = None
                if resp.status_code == 429:
                    try:
                        payload = resp.json()
                        retry_after = payload.get("parameters", {}).get("retry_after")
                    except Exception:
                        pass
                if attempt >= rt.max_retries:
                    raise TelegramHTTPError(resp.status_code, resp.text)
                self._maybe_sleep(rt, attempt, retry_after=retry_after)
                attempt += 1
                continue

            try:
                payload = resp.json()
            except ValueError as e:
                if attempt >= rt.max_retries:
                    raise TelegramHTTPError(resp.status_code, f"Invalid JSON: {resp.text[:200]}") from e
                self._maybe_sleep(rt, attempt, retry_after=None)
                attempt += 1
                continue

            if not payload.get("ok", False):
                params = payload.get("parameters") or {}
                desc = payload.get("description", "unknown error")
                error_code = payload.get("error_code", -1)
                retry_after = params.get("retry_after")
                transient = error_code in {429, 500, 502, 503, 504}
                if transient and attempt < rt.max_retries:
                    self._maybe_sleep(rt, attempt, retry_after=retry_after)
                    attempt += 1
                    continue
                raise TelegramAPIError(error_code, desc, parameters=params)

            return payload.get("result", payload)

    # --------- Helpers ---------
    def _runtime(self) -> _Runtime:
        """(Re)load .env and environment, return a runtime config object."""
        if load_dotenv:
            # reload .env each time (safe; doesn't override already-set env unless override=True)
            load_dotenv(override=False)

        token = os.getenv("TELEGRAM_BOT_TOKEN") or ""
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required (not found in env/.env)")

        chat_id = os.getenv("TELEGRAM_DEFAULT_CHAT_ID")
        base_url = os.getenv("TELEGRAM_BASE_URL", "https://api.telegram.org")
        timeout = int(os.getenv("TELEGRAM_TIMEOUT", "15"))
        max_retries = int(os.getenv("TELEGRAM_MAX_RETRIES", "4"))
        backoff_factor = float(os.getenv("TELEGRAM_BACKOFF_FACTOR", "0.75"))
        proxy = os.getenv("TELEGRAM_PROXY")

        return _Runtime(
            token=token,
            chat_id=chat_id,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            proxy=proxy,
        )

    @staticmethod
    def _maybe_sleep(rt: _Runtime, attempt: int, retry_after: Optional[int]) -> None:
        """Sleep between retries, respecting Telegram's retry_after when provided."""
        delay = float(retry_after) if retry_after is not None else rt.backoff_factor * (2 ** attempt)
        delay = min(delay, 30.0)
        if delay > 0:
            time.sleep(delay)

    @staticmethod
    def _chunk_text(text: str, n: int) -> Iterable[str]:
        """Yield text chunks ≤ n, splitting on paragraph boundaries when possible."""
        if len(text) <= n:
            yield text
            return
        parts = text.split("\n\n")
        buf = ""
        for p in parts:
            candidate = (buf + ("\n\n" if buf else "") + p)
            if len(candidate) <= n:
                buf = candidate
            else:
                if buf:
                    yield buf
                if len(p) <= n:
                    buf = p
                else:
                    for i in range(0, len(p), n):
                        chunk = p[i : i + n]
                        if chunk:
                            yield chunk
                    buf = ""
        if buf:
            yield buf

    @staticmethod
    def _format_trace(err: BaseException) -> str:
        """Return a compact traceback string."""
        tb = "".join(traceback.format_exception(type(err), err, err.__traceback__)).strip()
        if len(tb) > 3500:
            tb = tb[:3500] + "\n... (truncated)"
        return tb


# -----------------------
# Global handlers (sys/threading/logging)
# -----------------------
class TelegramLogHandler(logging.Handler):
    """Forward ERROR/CRITICAL logs to Telegram with a simple cooldown."""

    def __init__(self, notifier: TelegramNotifier, level: int = logging.ERROR, cooldown_seconds: float = 10.0):
        super().__init__(level)
        self.notifier = notifier
        self.cooldown = cooldown_seconds
        self._last_sent: Dict[str, float] = {}

    def emit(self, record: logging.LogRecord) -> None:
        try:
            key = f"{record.name}:{record.levelno}"
            now = time.time()
            last = self._last_sent.get(key, 0.0)
            if now - last < self.cooldown:
                return
            self._last_sent[key] = now

            title = "🚨 رویداد لاگ"
            hdr = f"سطح: {record.levelname}\nلوگر: {record.name}"
            base_msg = self.format(record)

            if record.exc_info:
                tb = "".join(traceback.format_exception(*record.exc_info)).strip()
                if len(tb) > 3000:
                    tb = tb[:3000] + "\n... (truncated)"
                body = f"{title}\n{hdr}\n\n📝 پیام: {base_msg}\n\n```\n{tb}\n```"
            else:
                body = f"{title}\n{hdr}\n\n📝 پیام: {base_msg}"

            self.notifier.send_message(body, parse_mode="Markdown")
        except Exception:
            try:
                self.handleError(record)
            except Exception:
                pass


def install_global_handlers(
    notifier: TelegramNotifier,
    *,
    hook_sys: bool = True,
    hook_threading: bool = True,
    hook_logging: bool = True,
    logging_level: int = logging.ERROR,
    logging_cooldown_seconds: float = 10.0,
) -> None:
    """Enable global monitoring so *any* module's uncaught errors & ERROR logs go to Telegram."""
    if hook_sys:
        import sys

        def _sys_hook(exc_type, exc, tb):  # type: ignore[override]
            try:
                notifier.notify_error(exc, context="uncaught: sys.excepthook")
            finally:
                sys.__excepthook__(exc_type, exc, tb)

        sys.excepthook = _sys_hook  # type: ignore[assignment]

    if hook_threading:
        import threading

        def _thread_hook(args: "threading.ExceptHookArgs") -> None:  # type: ignore[name-defined]
            try:
                name = getattr(args, "thread", None)
                tname = getattr(name, "name", "<unknown>")
                notifier.notify_error(args.exc_value, context=f"uncaught in thread: {tname}")
            finally:
                if hasattr(threading, "__excepthook__"):
                    try:
                        threading.__excepthook__(args)  # type: ignore[attr-defined]
                    except Exception:
                        pass

        if hasattr(threading, "excepthook"):
            threading.excepthook = _thread_hook  # type: ignore[assignment]

    if hook_logging:
        root = logging.getLogger()
        handler = TelegramLogHandler(notifier, level=logging_level, cooldown_seconds=logging_cooldown_seconds)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)
        if root.level == logging.NOTSET:
            root.setLevel(logging_level)


# Convenience alias (keep at end, after class is defined)
monitor_exceptions = TelegramNotifier.monitor_exceptions
