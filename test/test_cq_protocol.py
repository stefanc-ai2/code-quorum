from __future__ import annotations

import re

from cq_protocol import REQ_ID_PREFIX, make_req_id, wrap_request_prompt
from cq_protocol import FROM_PREFIX, REPLY_PREFIX, wrap_reply_payload
from cq_protocol import strip_trailing_markers


def test_make_req_id_format_and_uniqueness() -> None:
    ids = [make_req_id() for _ in range(2000)]
    assert len(set(ids)) == len(ids)
    for rid in ids:
        assert isinstance(rid, str)
        assert len(rid) == 32
        assert re.fullmatch(r"[0-9a-f]{32}", rid) is not None


def test_wrap_request_prompt_structure() -> None:
    req_id = make_req_id()
    message = "hello\nworld"
    prompt = wrap_request_prompt(message, req_id)

    assert prompt.startswith(f"{REQ_ID_PREFIX} {req_id}\n\n")
    assert prompt.endswith("hello\nworld\n")
    assert "IMPORTANT:" not in prompt


def test_strip_trailing_markers_removes_harness_trailers() -> None:
    text = "line1\nline2\nHARNESS_DONE\n\n"
    assert strip_trailing_markers(text) == "line1\nline2"


def test_wrap_reply_payload_structure() -> None:
    payload = wrap_reply_payload(reply_to_req_id="abc123", from_provider="codex", message="hello\nworld")
    assert payload.startswith(f"{REPLY_PREFIX} abc123\n{FROM_PREFIX} codex\n")
    assert "[CQ_RESULT] No reply required.\n\n" in payload
    assert payload.endswith("hello\nworld\n")
