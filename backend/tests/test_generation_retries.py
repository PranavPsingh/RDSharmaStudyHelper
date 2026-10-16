import pytest

from backend.app import generator


class TemporaryGeminiError(Exception):
    code = 503

    def __str__(self) -> str:
        return "503 UNAVAILABLE"


class InvalidRequestError(Exception):
    code = 400


def _no_jitter(start: float, stop: float) -> float:
    del start, stop
    return 0


def test_retries_transient_gemini_errors_with_exponential_backoff(monkeypatch) -> None:
    delays = []
    calls = 0
    monkeypatch.setattr(generator.random, "uniform", _no_jitter)
    monkeypatch.setattr(generator.time, "sleep", delays.append)

    def request() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TemporaryGeminiError()
        return "ok"

    assert generator._with_transient_retries(request, "test request") == "ok"
    assert calls == 3
    assert delays == [1, 2]


def test_does_not_retry_non_transient_gemini_errors(monkeypatch) -> None:
    delays = []
    monkeypatch.setattr(generator.time, "sleep", delays.append)

    with pytest.raises(InvalidRequestError):
        generator._with_transient_retries(
            lambda: (_ for _ in ()).throw(InvalidRequestError("bad request")),
            "test request",
        )

    assert delays == []


def test_raises_after_transient_retry_limit(monkeypatch) -> None:
    delays = []
    calls = 0
    monkeypatch.setattr(generator.random, "uniform", _no_jitter)
    monkeypatch.setattr(generator.time, "sleep", delays.append)

    def request() -> None:
        nonlocal calls
        calls += 1
        raise TemporaryGeminiError()

    with pytest.raises(TemporaryGeminiError):
        generator._with_transient_retries(request, "test request")

    assert calls == generator.TRANSIENT_RETRY_ATTEMPTS
    assert delays == [1, 2, 4, 8]


def test_diagram_transient_retries_are_capped_at_two(monkeypatch) -> None:
    delays = []
    calls = 0
    monkeypatch.setattr(generator.random, "uniform", _no_jitter)
    monkeypatch.setattr(generator.time, "sleep", delays.append)

    def request() -> None:
        nonlocal calls
        calls += 1
        raise TemporaryGeminiError()

    with pytest.raises(TemporaryGeminiError):
        generator._with_transient_retries(
            request,
            "diagram request",
            attempts=generator.DIAGRAM_TRANSIENT_RETRY_ATTEMPTS,
        )

    assert calls == 2
    assert delays == [1]
