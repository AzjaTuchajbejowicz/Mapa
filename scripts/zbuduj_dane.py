"""Buduje pliki build/osm_*.json (stanowiska, młyny, karczmy, pałace i zamki) z wyciągu OpenStreetMap
(plik GeoJSON Sequence z `osmium export`). Uruchamiane przez GitHub Actions."""
import json, sys, datetime

KEEP = {"name", "name:pl", "alt_name", "site_type", "archaeological_site", "fortification_type", "historic",
        "historic:civilization", "historic:period", "historic:era", "start_date", "construction_date",
        "description", "description:pl", "note", "note:pl", "wikipedia", "wikipedia:pl", "wikidata",
        "heritage", "heritage:operator", "ref:nid", "man_made", "building", "historic:building", "ruins",
        "windmill:type", "windmill_type", "castle_type", "ruins:historic", "architect"}
PREFIXES = ("disused:", "abandoned:", "ruins:", "demolished:", "was:", "razed:", "destroyed:")
MILL = {"watermill", "windmill", "mill"}


def coords(g):
    t, c = g.get("type"), g.get("coordinates") or []
    if t == "Point": return [c]
    if t in ("LineString", "MultiPoint"): return c
    if t == "Polygon": return c[0] if c else []
    if t == "MultiLineString": return [p for l in c for p in l]
    if t == "MultiPolygon": return [p for poly in c for p in poly[0]]
    return []


def is_mill(t):
    for p in ("",) + PREFIXES:
        for k in ("man_made", "building"):
            if t.get(p + k) in MILL:
                return True
    return t.get("historic") in MILL


INN = __import__("re").compile(r"karczm|austeri|zajazd|krczm|kretscham|krug\b", __import__("re").I)


def inn_kind(t):
    """Zabytkowa karczma (budynek) albo miejsce, którego nazwa pochodzi od karczmy."""
    name = " ".join(t.get(k, "") for k in ("name", "name:pl", "old_name", "alt_name", "historic:name"))
    if not INN.search(name) and t.get("building") != "inn" and t.get("historic") != "inn":
        return None
    if t.get("place"):
        return "place"
    if t.get("historic") or t.get("heritage") or t.get("building") == "inn":
        return "building"
    return None


CASTLE_NAME = __import__("re").compile(r"pałac|zam[eo]k|dw[oó]r|kasztel", __import__("re").I)


def castle_kind(t):
    """Pałac, zamek albo dwór (także ruiny) według tagów OpenStreetMap."""
    hist, bld, ct = t.get("historic", ""), t.get("building", ""), t.get("castle_type", "")
    if not (hist in ("castle", "manor", "palace") or bld in ("castle", "palace") or t.get("ruins:historic") in ("castle", "manor", "palace")):
        return None
    name = t.get("name", "")
    if ct in ("palace", "stately") or bld == "palace" or hist == "palace" or __import__("re").search(r"pałac", name, __import__("re").I):
        return "palac"
    if ct == "manor" or hist == "manor" or __import__("re").search(r"dw[oó]r|dworek", name, __import__("re").I):
        return "dwor"
    return "zamek"


sites, mills, inns, castles, seen = [], [], [], [], set()
with open(sys.argv[1], encoding="utf-8") as f:
    for line in f:
        line = line.strip().lstrip("\x1e")
        if not line:
            continue
        ft = json.loads(line)
        pr = ft.get("properties") or {}
        typ, oid = pr.get("@type"), pr.get("@id")
        if (typ, oid) in seen:
            continue
        pts = coords(ft.get("geometry") or {})
        if not pts:
            continue
        lon = sum(p[0] for p in pts) / len(pts)
        lat = sum(p[1] for p in pts) / len(pts)
        tags = {k: v for k, v in pr.items() if not k.startswith("@") and
                (k in KEEP or (k.startswith(PREFIXES) and k.split(":", 1)[1] in ("man_made", "building")))}
        el = {"type": typ, "id": oid, "lat": round(lat, 6), "lon": round(lon, 6), "tags": tags}
        if pr.get("historic") in ("archaeological_site", "tumulus"):
            sites.append(el); seen.add((typ, oid))
        elif is_mill(pr):
            mills.append(el); seen.add((typ, oid))
        elif castle_kind(pr):
            el["tags"]["kind"] = castle_kind(pr)
            for k in ("historic", "heritage", "ruins"):
                if pr.get(k): el["tags"][k] = pr[k]
            castles.append(el); seen.add((typ, oid))
        elif inn_kind(pr):
            el["tags"]["kind"] = inn_kind(pr)
            for k in ("place", "old_name", "heritage", "historic"):
                if pr.get(k): el["tags"][k] = pr[k]
            inns.append(el); seen.add((typ, oid))

today = datetime.date.today().isoformat()
minimum = int(sys.argv[2]) if len(sys.argv) > 2 else 100
for name, items in (("stanowiska", sites), ("mlyny", mills), ("karczmy_osm", inns), ("palace_zamki", castles)):
    if len(items) < (minimum if name != "karczmy_osm" else min(minimum, 10)):
        raise SystemExit(f"Podejrzanie mało obiektów w {name}: {len(items)}")
    with open(f"build/osm_{name}.json", "w", encoding="utf-8") as f:
        json.dump({"generated": today, "count": len(items), "elements": items}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{name}: {len(items)} obiektów")
