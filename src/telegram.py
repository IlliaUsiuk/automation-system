"""Minimal Telegram Bot API client - stdlib urllib only, same approach
github_sync.py already uses for GitHub, so this doesn't add an HTTP client
dependency for a small, low-volume integration. Shared by the registration
route (sends the admin a confirmation code) and telegram_bot.py (polls for
the admin's "/grant"/"/revoke" replies)."""
import json
import os
import urllib.error
import urllib.request

API_URL = "https://api.telegram.org/bot{token}/{method}"


def _call(method, payload, timeout=10):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
    url = API_URL.format(token=token, method=method)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError):
        return None


def send_message(chat_id, text):
    """Best-effort - returns False on any failure (missing token, chat_id,
    network) rather than raising, since a failed notification shouldn't ever
    break the registration flow itself."""
    if not chat_id:
        return False
    result = _call("sendMessage", {"chat_id": chat_id, "text": text})
    return bool(result and result.get("ok"))


def get_updates(offset=None, timeout=25):
    """Long-polls getUpdates. `timeout` is Telegram's own long-poll window
    (seconds) - the HTTP request timeout is kept a bit longer than that so a
    slow-but-still-arriving response isn't cut off right before Telegram
    would have replied anyway."""
    payload = {"timeout": timeout}
    if offset is not None:
        payload["offset"] = offset
    result = _call("getUpdates", payload, timeout=timeout + 10)
    if not result or not result.get("ok"):
        return []
    return result["result"]
