from __future__ import annotations

import re
import secrets

REQ_ID_PREFIX = "CQ_REQ_ID:"
REPLY_PREFIX = "CQ_REPLY:"
FROM_PREFIX = "CQ_FROM:"

_TRAILING_DONE_TAG_RE = re.compile(
    r"^\s*[A-Z][A-Z0-9_]*_DONE(?:\s*:\s*(?:[0-9a-f]{32}|\d{8}-\d{6}-\d{3}-\d+))?\s*$"
)


def _is_trailing_noise_line(line: str) -> bool:
    if (line or "").strip() == "":
        return True
    # Some harnesses append a generic completion tag after a response.
    # Treat it as ignorable trailer.
    return bool(_TRAILING_DONE_TAG_RE.match(line or ""))


def strip_trailing_markers(text: str) -> str:
    """
    Remove trailing harness marker lines (blank lines and `*_DONE` tags).

    This is meant for "recall"/display commands where we want a clean view of the reply.
    """
    lines = [ln.rstrip("\n") for ln in (text or "").splitlines()]
    while lines:
        last = lines[-1]
        if _is_trailing_noise_line(last):
            lines.pop()
            continue
        break
    return "\n".join(lines).rstrip()


def make_req_id() -> str:
    # 32-hex id (token_hex(16)) for compactness and uniqueness.
    return secrets.token_hex(16)


def wrap_request_prompt(message: str, req_id: str) -> str:
    """
    Wrap a user message for a provider request that will be correlated by `CQ_REQ_ID`.

    This wrapper intentionally does *not* include completion markers.
    Completion/correlation is handled via reply-via-ask (`ask --reply-to <req_id> ...`) in higher-level flows.
    """
    message = (message or "").rstrip()
    return (
        f"{REQ_ID_PREFIX} {req_id}\n\n"
        f"{message}\n"
    )


def wrap_reply_payload(
    *, reply_to_req_id: str, from_provider: str, message: str
) -> str:
    """
    Wrap a result/notification payload for reply-via-ask.
    """
    reply_to_req_id = str(reply_to_req_id or "").strip()
    from_provider = str(from_provider or "").strip()
    message = (message or "").rstrip()
    return (
        f"{REPLY_PREFIX} {reply_to_req_id}\n"
        f"{FROM_PREFIX} {from_provider}\n"
        "[CQ_RESULT] No reply required.\n\n"
        f"{message}\n"
    )
