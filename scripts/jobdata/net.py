"""Small HTTP helper: retries, timeouts, a polite User-Agent, clear errors."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

# BLS asks automated clients to send a User-Agent with contact info.
# Set JOBDATA_CONTACT to your email to be a good citizen.
_CONTACT = os.environ.get("JOBDATA_CONTACT", "learner@example.com")
USER_AGENT = f"ai-job-course-kit/1.0 (+contact: {_CONTACT})"


class FetchError(RuntimeError):
    """Raised when a live pull fails. Callers must stop, not guess."""


def fetch(url: str, *, timeout: int = 30, retries: int = 3, binary: bool = False,
          headers: dict | None = None):
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if binary:
                    return data
                charset = resp.headers.get_content_charset() or "utf-8"
                return data.decode(charset, errors="replace")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (400, 401, 403, 404):
                break  # not worth retrying
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
        time.sleep(2 ** attempt)
    raise FetchError(f"Live pull failed for {url}: {last_err}")


def fetch_json(url: str, **kw):
    text = fetch(url, **kw)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise FetchError(f"Expected JSON from {url}, got something else: {e}") from e
