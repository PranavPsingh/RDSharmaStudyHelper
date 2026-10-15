from backend.app.svg_sanitize import sanitize_svg


EXAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240" stroke="black" fill="none" stroke-width="2" font-family="sans-serif" font-size="16"><polygon points="70,40 70,190 270,190"/><polyline points="70,170 90,170 90,190" stroke-width="1.5"/><g fill="black" stroke="none"><text x="52" y="40">A</text><text x="52" y="208">B</text><text x="276" y="208">C</text><text x="64" y="120" text-anchor="end">3 cm</text><text x="160" y="212">4 cm</text><text x="180" y="105">x</text></g></svg>"""


def test_removes_script_element() -> None:
    result = sanitize_svg('<svg viewBox="0 0 10 10"><script>alert(1)</script><circle r="2"/></svg>')

    assert result is not None
    assert "<script" not in result
    assert "<circle" in result


def test_removes_event_handler_attribute() -> None:
    result = sanitize_svg('<svg viewBox="0 0 10 10" onload="alert(1)"><circle r="2"/></svg>')

    assert result is not None
    assert "onload" not in result


def test_replaces_non_black_and_white_stroke() -> None:
    result = sanitize_svg('<svg viewBox="0 0 10 10"><line stroke="red"/></svg>')

    assert result is not None
    assert 'stroke="black"' in result


def test_invalid_xml_returns_none() -> None:
    assert sanitize_svg("<svg><circle></svg>") is None


def test_example_svg_round_trips_with_polygon() -> None:
    result = sanitize_svg(EXAMPLE_SVG)

    assert result is not None
    assert "<polygon" in result
    assert 'viewBox="0 0 320 240"' in result
