#!/usr/bin/env python3
"""Lint a .drawio file for the layout faults a reader notices immediately.

    python3 check.py <file.drawio> [--min-gap 20] [--page 0] [--json] [--quiet]

Checks (errors fail the run, warnings do not):

    ERROR   shape overlap          two shapes partially cover each other
    ERROR   edge through a shape   a connection is routed across a node it does not touch
    ERROR   unlabeled connection   an edge with no label on it or under it
    WARN    crowding               two shapes closer than --min-gap px
    WARN    no icons               no shape uses a real service/stencil icon

This is a geometry check, not a taste check: it cannot tell you the diagram reads well,
matches the brand, or uses the right layout. Render it and look at it too — see
`/diagram:review`.

Edge routing is evaluated as straight segments between the points draw.io stores
(source → waypoints → target). A right-angle edge drawn by the renderer can therefore
differ slightly from what is checked here; treat a reported crossing as a place to look,
and fix it by adding waypoints that route through empty space.

Exit codes: 0 clean (warnings allowed) · 1 errors found · 2 the file could not be read.
"""

import argparse
import base64
import json
import os
import sys
import urllib.parse
import zlib
import xml.etree.ElementTree as ET

# A shape may sit this far inside another before it counts as an overlap, and an edge
# may cut this far into a shape before it counts as crossing it. Absorbs rounding and
# border widths without hiding a real fault.
EPS = 2.0


# ─── Model ────────────────────────────────────────────────────────────────────


class Cell:
    __slots__ = (
        "id",
        "parent",
        "style",
        "value",
        "is_vertex",
        "is_edge",
        "source",
        "target",
        "geom",
        "points",
        "relative",
    )

    def __init__(self, el):
        self.id = el.get("id", "")
        self.parent = el.get("parent", "")
        self.style = el.get("style", "") or ""
        self.value = (el.get("value", "") or "").strip()
        self.is_vertex = el.get("vertex") == "1"
        self.is_edge = el.get("edge") == "1"
        self.source = el.get("source", "")
        self.target = el.get("target", "")
        self.geom = None  # (x, y, w, h) as authored, relative to the parent
        self.points = []  # explicit edge geometry: source point, waypoints, target point
        self.relative = False

        g = el.find("mxGeometry")
        if g is None:
            return
        self.relative = g.get("relative") == "1"
        try:
            self.geom = (
                float(g.get("x", 0) or 0),
                float(g.get("y", 0) or 0),
                float(g.get("width", 0) or 0),
                float(g.get("height", 0) or 0),
            )
        except ValueError:
            self.geom = None
        src_pt = tgt_pt = None
        for pt in g.findall("mxPoint"):
            try:
                xy = (float(pt.get("x", 0) or 0), float(pt.get("y", 0) or 0))
            except ValueError:
                continue
            if pt.get("as") == "sourcePoint":
                src_pt = xy
            elif pt.get("as") == "targetPoint":
                tgt_pt = xy
        waypoints = []
        for arr in g.findall("Array"):
            if arr.get("as") != "points":
                continue
            for pt in arr.findall("mxPoint"):
                try:
                    waypoints.append(
                        (float(pt.get("x", 0) or 0), float(pt.get("y", 0) or 0))
                    )
                except ValueError:
                    pass
        self.points = [src_pt, waypoints, tgt_pt]


def _decode_diagram(node):
    """Return the mxGraphModel element of a <diagram>, inflating a compressed page."""
    model = node.find("mxGraphModel")
    if model is not None:
        return model
    payload = (node.text or "").strip()
    if not payload:
        return None
    try:
        raw = zlib.decompress(base64.b64decode(payload), -15).decode("utf-8")
        return ET.fromstring(urllib.parse.unquote(raw))
    except Exception:
        return None


def load(path, page=0):
    """Return (page_name, {id: Cell}) for one page of a .drawio file."""
    root = ET.parse(path).getroot()
    pages = root.findall("diagram") if root.tag == "mxfile" else []
    if pages:
        if page >= len(pages):
            raise ValueError(f"page {page} not found — the file has {len(pages)}")
        node = pages[page]
        name = node.get("name", f"page {page}")
        model = _decode_diagram(node)
        if model is None:
            raise ValueError(
                "could not read the page (compressed with an unknown encoding?)"
            )
    else:  # a bare mxGraphModel / mxfile without <diagram>
        name, model = (
            "page 0",
            (root if root.tag == "mxGraphModel" else root.find(".//mxGraphModel")),
        )
        if model is None:
            raise ValueError("no mxGraphModel found")
    cells = {}
    for el in model.iter("mxCell"):
        cell = Cell(el)
        if cell.id:
            cells[cell.id] = cell
    # A shape wrapped in an <object ...><mxCell/></object> carries its label on the object.
    for obj in model.iter("object"):
        inner = obj.find("mxCell")
        if inner is None:
            continue
        cell = Cell(inner)
        cell.id = obj.get("id", cell.id)
        cell.value = (obj.get("label", "") or cell.value).strip()
        if cell.id:
            cells[cell.id] = cell
    return name, cells


# ─── Geometry ─────────────────────────────────────────────────────────────────


def _ancestors(cell, cells):
    seen, cur = [], cells.get(cell.parent)
    while cur is not None and cur.id not in seen:
        seen.append(cur.id)
        cur = cells.get(cur.parent)
    return seen


def absolute_rects(cells):
    """{id: (x, y, w, h)} in page coordinates for every real shape.

    Excludes edges, edge labels, zero-size cells, and pure text labels — a caption
    sitting on a container is not an overlap fault.
    """
    rects = {}
    for cid, c in cells.items():
        if not c.is_vertex or not c.geom or c.relative:
            continue
        x, y, w, h = c.geom
        if w <= 0 or h <= 0:
            continue
        parent = cells.get(c.parent)
        if parent is not None and parent.is_edge:  # edge label
            continue
        style = c.style
        if "text;" in style or style.startswith("text") or "edgeLabel" in style:
            continue
        # Child coordinates are relative to the parent shape — walk up to page space.
        cur = parent
        guard = 0
        while cur is not None and cur.is_vertex and cur.geom and guard < 50:
            x += cur.geom[0]
            y += cur.geom[1]
            cur = cells.get(cur.parent)
            guard += 1
        rects[cid] = (x, y, w, h)
    return rects


def _overlap(a, b):
    """Overlapping width/height of two rects (negative = the gap between them)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (min(ax + aw, bx + bw) - max(ax, bx), min(ay + ah, by + bh) - max(ay, by))


def _contains(outer, inner):
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return (
        ox - EPS <= ix
        and oy - EPS <= iy
        and ox + ow + EPS >= ix + iw
        and oy + oh + EPS >= iy + ih
    )


def _center(r):
    return (r[0] + r[2] / 2.0, r[1] + r[3] / 2.0)


def _seg_hits_rect(p, q, rect):
    """True if segment p→q enters `rect` (inset by EPS so touching an edge is fine)."""
    x, y, w, h = rect[0] + EPS, rect[1] + EPS, rect[2] - 2 * EPS, rect[3] - 2 * EPS
    if w <= 0 or h <= 0:
        return False
    inside = lambda pt: x <= pt[0] <= x + w and y <= pt[1] <= y + h  # noqa: E731
    if inside(p) or inside(q):
        return True
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return any(
        _segments_cross(p, q, corners[i], corners[(i + 1) % 4]) for i in range(4)
    )


def _segments_cross(p1, p2, p3, p4):
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)

    o1, o2, o3, o4 = (
        orient(p1, p2, p3),
        orient(p1, p2, p4),
        orient(p3, p4, p1),
        orient(p3, p4, p2),
    )
    if o1 != o2 and o3 != o4:
        return True
    on = lambda a, b, c: (  # collinear point c on segment ab  # noqa: E731
        min(a[0], b[0]) - 1e-9 <= c[0] <= max(a[0], b[0]) + 1e-9
        and min(a[1], b[1]) - 1e-9 <= c[1] <= max(a[1], b[1]) + 1e-9
    )
    return (
        (o1 == 0 and on(p1, p2, p3))
        or (o2 == 0 and on(p1, p2, p4))
        or (o3 == 0 and on(p3, p4, p1))
        or (o4 == 0 and on(p3, p4, p2))
    )


def edge_route(edge, cells, rects):
    """The polyline draw.io stores for an edge: source → waypoints → target."""
    src_pt, waypoints, tgt_pt = edge.points if edge.points else (None, [], None)
    start = rects.get(edge.source)
    end = rects.get(edge.target)
    start = _center(start) if start else src_pt
    end = _center(end) if end else tgt_pt
    if start is None or end is None:
        return []
    return [start, *waypoints, end]


# ─── Checks ───────────────────────────────────────────────────────────────────


def label_of(cell, cells):
    if cell.value:
        return cell.value
    for c in cells.values():  # a label parented to the edge counts
        if c.parent == cell.id and c.value:
            return c.value
    return ""


def name_of(cid, cells):
    c = cells.get(cid)
    text = (c.value if c else "") or ""
    text = " ".join(text.replace("&#10;", " ").split())
    text = text if len(text) <= 40 else text[:37] + "..."
    return f"{text or '(unnamed)'} [{cid}]"


def check(cells, min_gap=20.0, allow_unlabeled=False):
    rects = absolute_rects(cells)
    errors, warnings, stats = [], [], {}
    ids = sorted(rects)

    # 1 + 2. Shape overlap and crowding. Nesting (one shape fully inside another) is a
    # grouping, not a fault — only partial overlap is.
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            if a in _ancestors(cells[b], cells) or b in _ancestors(cells[a], cells):
                continue
            ra, rb = rects[a], rects[b]
            ox, oy = _overlap(ra, rb)
            if ox > EPS and oy > EPS:
                if _contains(ra, rb) or _contains(rb, ra):
                    continue
                errors.append(
                    (
                        "shape overlap",
                        f"{name_of(a, cells)} overlaps {name_of(b, cells)} "
                        f"by {ox:.0f}×{oy:.0f}px",
                    )
                )
            elif ox > -min_gap and oy > -min_gap:
                gap = max(0.0, max(-ox, -oy))
                # Shapes that touch exactly are stacked on purpose (legend rows, table
                # bands); only a real-but-too-small gap is crowding.
                if gap >= 1.0:
                    warnings.append(
                        (
                            "crowding",
                            f"{name_of(a, cells)} and {name_of(b, cells)} are {gap:.0f}px "
                            f"apart (min {min_gap:.0f}px)",
                        )
                    )

    # 3 + 4. Edge routing and labels.
    edges = [c for c in cells.values() if c.is_edge]
    stats["edges"] = len(edges)
    for e in edges:
        if not label_of(e, cells):
            ends = (
                f"{name_of(e.source, cells)} → {name_of(e.target, cells)}"
                if e.source or e.target
                else f"[{e.id}]"
            )
            bucket = warnings if allow_unlabeled else errors
            bucket.append(("unlabeled connection", f"edge {ends} has no label"))
        route = edge_route(e, cells, rects)
        if len(route) < 2:
            continue
        endpoints = {e.source, e.target}
        skip = set(endpoints)
        for end in endpoints:
            if end in cells:
                skip.update(_ancestors(cells[end], cells))
        src_rect, tgt_rect = rects.get(e.source), rects.get(e.target)
        hit = []
        for cid in ids:
            if cid in skip:
                continue
            # A container holding one of the endpoints is crossed by definition when the
            # edge leaves it — that is not a routing fault.
            if (src_rect and _contains(rects[cid], src_rect)) or (
                tgt_rect and _contains(rects[cid], tgt_rect)
            ):
                continue
            if any(
                _seg_hits_rect(route[i], route[i + 1], rects[cid])
                for i in range(len(route) - 1)
            ):
                hit.append(cid)
        for cid in hit:
            errors.append(
                (
                    "edge through a shape",
                    f"edge {name_of(e.source, cells)} → {name_of(e.target, cells)} "
                    f"crosses {name_of(cid, cells)}",
                )
            )

    # 5. Icon usage — a diagram of plain rectangles is the classic generic-looking output.
    icon_markers = ("image=", "shape=mxgraph.", "sketch=", "mscae/", "resIcon=")
    icons = sum(1 for cid in ids if any(m in cells[cid].style for m in icon_markers))
    stats["shapes"] = len(ids)
    stats["shapes_with_icons"] = icons
    if ids and icons == 0:
        warnings.append(
            (
                "no icons",
                f"none of the {len(ids)} shapes use a service/stencil icon — plain boxes read "
                f"as generic; use the real icon set for major components",
            )
        )
    return errors, warnings, stats


# ─── Reporting ────────────────────────────────────────────────────────────────


def report(path, page_name, errors, warnings, stats, quiet=False):
    print(
        f"{os.path.basename(path)} — {page_name}: "
        f"{stats.get('shapes', 0)} shapes, {stats.get('edges', 0)} edges, "
        f"{stats.get('shapes_with_icons', 0)} with icons"
    )
    for kind, items in (("ERROR", errors), ("WARN", warnings)):
        if quiet and kind == "WARN":
            continue
        for rule, message in items:
            print(f"  {kind:<5} {rule:<22} {message}")
    if not errors and not warnings:
        print("  clean — no geometry faults found")
    elif not errors:
        print(f"  no errors ({len(warnings)} warning(s))")
    print("\n  Geometry only. Render it and read the PNG before delivering:")
    print("    python3 render.py <file.drawio>")


def main(argv=None):
    p = argparse.ArgumentParser(description="Lint a .drawio file for layout faults.")
    p.add_argument("file", help="the .drawio file to check")
    p.add_argument("--page", type=int, default=0, help="page index (default: 0)")
    p.add_argument(
        "--min-gap",
        type=float,
        default=20.0,
        help="minimum whitespace between shapes, px (default: 20)",
    )
    p.add_argument(
        "--allow-unlabeled",
        action="store_true",
        help="unlabeled connections warn instead of failing (sequential flows)",
    )
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--quiet", action="store_true", help="errors only")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        page_name, cells = load(os.path.expanduser(args.file), args.page)
    except (ET.ParseError, ValueError, OSError) as exc:
        print(f"ERROR: cannot read {args.file} — {exc}", file=sys.stderr)
        return 2

    errors, warnings, stats = check(cells, args.min_gap, args.allow_unlabeled)
    if args.json:
        print(
            json.dumps(
                {
                    "file": args.file,
                    "page": page_name,
                    "stats": stats,
                    "errors": [{"rule": r, "message": m} for r, m in errors],
                    "warnings": [{"rule": r, "message": m} for r, m in warnings],
                },
                indent=2,
            )
        )
    else:
        report(args.file, page_name, errors, warnings, stats, args.quiet)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
