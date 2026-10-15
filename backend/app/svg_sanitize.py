from xml.etree.ElementTree import Element, tostring

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

ALLOWED_ELEMENTS = {
    "svg",
    "g",
    "line",
    "polyline",
    "polygon",
    "path",
    "circle",
    "ellipse",
    "rect",
    "text",
    "tspan",
    "defs",
    "marker",
}
ALLOWED_ATTRIBUTES = {
    "xmlns",
    "viewBox",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "width",
    "height",
    "points",
    "d",
    "transform",
    "stroke",
    "stroke-width",
    "stroke-dasharray",
    "fill",
    "font-size",
    "font-family",
    "text-anchor",
    "dominant-baseline",
    "id",
    "marker-start",
    "marker-end",
    "markerWidth",
    "markerHeight",
    "refX",
    "refY",
    "orient",
}
ALLOWED_COLORS = {"none", "black", "white", "#000", "#000000", "#fff", "#ffffff"}
SVG_NAMESPACE = "http://www.w3.org/2000/svg"


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _copy_element(source: Element, *, is_root: bool = False) -> Element | None:
    tag = _local_name(source.tag)
    if tag not in ALLOWED_ELEMENTS:
        return None

    target = Element(tag)
    for name, raw_value in source.attrib.items():
        attribute = name
        if attribute not in ALLOWED_ATTRIBUTES or (is_root and attribute in {"width", "height"}):
            continue

        value = raw_value
        if attribute in {"stroke", "fill"}:
            normalized = value.strip().lower()
            value = normalized if normalized in ALLOWED_COLORS else ("black" if attribute == "stroke" else "none")
        target.set(attribute, value)

    if is_root and "xmlns" not in target.attrib:
        if source.tag.startswith("{"):
            target.set("xmlns", source.tag[1:].split("}", 1)[0])
        else:
            target.set("xmlns", SVG_NAMESPACE)

    target.text = source.text
    for child in source:
        copied = _copy_element(child)
        if copied is not None:
            target.append(copied)
            copied.tail = child.tail
        elif child.tail:
            if len(target):
                target[-1].tail = (target[-1].tail or "") + child.tail
            else:
                target.text = (target.text or "") + child.tail
    return target


def sanitize_svg(svg: str | None) -> str | None:
    if not svg or len(svg) > 20000:
        return None

    try:
        parsed = ElementTree.fromstring(svg)
    except (ElementTree.ParseError, DefusedXmlException, ValueError):
        return None

    if _local_name(parsed.tag) != "svg" or "viewBox" not in parsed.attrib:
        return None

    sanitized = _copy_element(parsed, is_root=True)
    if sanitized is None:
        return None
    return tostring(sanitized, encoding="unicode", short_empty_elements=True)
