import json
import re
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(name):
    return json.loads((ROOT / "content" / name).read_text(encoding="utf-8"))


def load_exhibits():
    exhibits = read_json("exhibits.json")
    world = read_json("garden.json")
    size = world["tileSize"]
    cols, rows = world["width"] // size, world["height"] // size
    blocked = set()
    for y in range(rows):
        for x in range(cols):
            if any(x * size < o["x"] + o["width"] and (x + 1) * size > o["x"]
                   and y * size < o["y"] + o["height"] and (y + 1) * size > o["y"]
                   for o in world["obstacles"]):
                blocked.add((x, y))
    result = {}
    for exhibit in exhibits:
        ident = exhibit["id"]
        tile = (exhibit["tile"]["x"], exhibit["tile"]["y"])
        if ident in result or not re.fullmatch(r"[a-z][a-z0-9-]*", ident) or exhibit["kind"] != "art":
            raise ValueError(f"Invalid or duplicate exhibit: {ident}")
        if not all(isinstance(v, int) for v in tile) or not (0 <= tile[0] < cols and 0 <= tile[1] < rows) or tile in blocked:
            raise ValueError(f"Blocked or out-of-bounds exhibit: {ident}")
        public = (ROOT / "frontend" / "public").resolve()
        asset = (public / exhibit["asset"].lstrip("/")).resolve()
        if not asset.is_relative_to(public) or not asset.is_file():
            raise ValueError(f"Missing or invalid asset: {ident}")
        if not all(isinstance(exhibit.get(k), str) and exhibit[k].strip() for k in ("title", "description", "alt")):
            raise ValueError(f"Missing exhibit text: {ident}")
        blocked.add(tile)
        result[ident] = exhibit
    start = (world["spawn"]["x"] // size, world["spawn"]["y"] // size)
    if start in blocked:
        raise ValueError("Spawn is obstructed")
    reachable, pending = {start}, deque([start])
    while pending:
        x, y = pending.popleft()
        for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= point[0] < cols and 0 <= point[1] < rows and point not in blocked and point not in reachable:
                reachable.add(point)
                pending.append(point)
    for exhibit in exhibits:
        x, y = exhibit["tile"]["x"], exhibit["tile"]["y"]
        if not any(p in reachable for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))):
            raise ValueError(f"Unreachable exhibit: {exhibit['id']}")
    return result
