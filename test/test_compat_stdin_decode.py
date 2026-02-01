from __future__ import annotations

import compat


def test_decode_stdin_bytes_decodes_utf8(monkeypatch) -> None:
    monkeypatch.delenv("CQ_STDIN_ENCODING", raising=False)
    raw = "你好".encode("utf-8")
    assert compat.decode_stdin_bytes(raw) == "你好"


def test_decode_stdin_bytes_honors_forced_encoding(monkeypatch) -> None:
    monkeypatch.setenv("CQ_STDIN_ENCODING", "latin-1")
    raw = "caf\xe9".encode("latin-1")
    assert compat.decode_stdin_bytes(raw) == "café"


def test_decode_stdin_bytes_never_emits_surrogates() -> None:
    # Invalid UTF-8 byte 0x80 should not end up as a lone surrogate (e.g. \udc80).
    out = compat.decode_stdin_bytes(b"abc\x80def")
    assert "\udc80" not in out


def test_decode_stdin_bytes_honors_utf16le_bom() -> None:
    raw = b"\xff\xfe" + "你好".encode("utf-16le")
    assert compat.decode_stdin_bytes(raw) == "你好"
