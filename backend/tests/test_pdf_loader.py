from backend.app.pdf_loader import sample_text


def test_sample_text_returns_short_text_unchanged() -> None:
    assert sample_text("short text", limit=20) == "short text"


def test_sample_text_takes_spread_out_windows() -> None:
    text = "0123456789" * 10

    assert sample_text(text, limit=12, windows=3) == "0123\n...\n2345\n...\n4567"
    assert sample_text(text, limit=12, phase=0.5, windows=3) == "6789\n...\n8901\n...\n0123"


def test_sample_text_moves_window_start_past_nearby_newline() -> None:
    text = "0123456789\nABCDEFGHIJ\nabcdefghij\nklmnopqrst"

    assert sample_text(text, limit=12, windows=3) == "ABCD\n...\nabcd\n...\nklmn"
