# -*- coding: utf-8 -*-
"""T-002: FakeProvider unit tests + sample_project isolation test."""
import pytest

from providers.base import BaseProvider, Message
from tests.fakes.fake_provider import FakeProvider


def test_conforms_to_base_provider():
    assert isinstance(FakeProvider(), BaseProvider)
    assert FakeProvider().is_available() is True
    assert FakeProvider(available=False).is_available() is False


def test_scripted_responses_then_default():
    fp = FakeProvider(responses=["one", "two"])
    assert fp.send("a") == "one"
    assert fp.send("b") == "two"
    assert fp.send("c") == fp.default_response


def test_call_recording():
    fp = FakeProvider(responses=["ok"])
    hist = [Message(role="user", content="earlier")]
    fp.send("hello", history=hist, system_prompt="sys")
    assert fp.call_count == 1
    call = fp.last_call
    assert call.method == "send"
    assert call.prompt == "hello"
    assert call.history == hist
    assert call.system_prompt == "sys"


def test_responder_callable():
    fp = FakeProvider(responder=lambda p, h, s: f"echo:{p}")
    assert fp.send("xyz") == "echo:xyz"


def test_failure_injection_next_and_always():
    fp = FakeProvider(responses=["fine"])
    fp.fail_next(TimeoutError("boom"))
    with pytest.raises(TimeoutError):
        fp.send("will fail")
    assert fp.send("recovers") == "fine"

    fp.fail_always = ValueError("dead")
    with pytest.raises(ValueError):
        fp.send("always fails")


def test_stream_chunks_reassemble():
    fp = FakeProvider(responses=["a fairly long streamed response text"])
    chunks = list(fp.stream("go"))
    assert len(chunks) > 1
    assert "".join(chunks) == "a fairly long streamed response text"
    assert fp.last_call.method == "stream"


def test_sample_project_fixture_isolated(sample_project):
    """Fixture yields a tmp copy: mutations must not touch the source tree."""
    env = sample_project / ".env"
    assert env.exists() and "FAKE" in env.read_text()
    assert (sample_project / "src" / "auth.py").exists()
    # mutate the copy
    (sample_project / "index.html").write_text("MUTATED")
    # source of truth untouched
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"
    assert "MUTATED" not in (src / "index.html").read_text()
