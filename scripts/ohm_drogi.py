"""Pobiera z OpenHistoricalMap drogi w Polsce oznaczone datą sprzed 1900 r. (albo zlikwidowane przed 1950 r.)
i zapisuje je jako data/drogi_ohm.json. Uruchamiane przez GitHub Actions."""
import json, re, time, datetime, urllib.parse, urllib.request

URL = "https://overpass-api.openhistoricalmap.org/api/interpreter"
UA = {"User-Agent": "mapa-detektorysty/1.0 (https://github.com/AzjaTuchajbejowicz/Mapa)"}
BB = "(49.0,14.1,54.9,24.2)"
HW = "^(motorway|trunk|primary|secondary|tertiary|unclassified|road|track|path|bridleway)$"
Q = f'[out:json][timeout:600];(way["highway"~"{HW}"]["start_date"]{BB};way["highway"~"{HW}"]["end_date"]{BB};);out tags geom;'


def year(v):
    m = re.search(r"(\d{3,4})", v or "")
    return int(m.group(1)) if m else None


def load_poly(path="build/poland.poly"):
    rings, cur = [], None
    try:
        for line in open(path, encoding="utf-8"):
            t = line.split()
            if not t: continue
            if t[0] == "END":
                if cur is not None: rings.append(cur); cur = None
                continue
            if len(t) == 2:
                try: cur.append((float(t[0]), float(t[1])))
                except (ValueError, AttributeError): pass
            elif cur is None and t[0] not in ("poland", "polska"):
                cur = []
    except FileNotFoundError:
        return None
    return [r for r in rings if len(r) > 2]


def inside(lat, lon, rings):
    if not rings: return 49.0 < lat < 54.9 and 14.1 < lon < 24.2
    res = False
    for r in rings:
        j = len(r) - 1
        for i in range(len(r)):
            xi, yi = r[i]; xj, yj = r[j]
            if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                res = not res
            j = i
    return res


def simplify(pts, tol=0.00015):
    """Douglas-Peucker na stopniach (ok. 10–15 m)."""
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[1] - a[1], b[0] - a[0]
    n = (dx * dx + dy * dy) ** .5 or 1e-12
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        p = pts[i]
        d = abs(dy * (p[1] - a[1]) - dx * (p[0] - a[0])) / n
        if d > dmax: dmax, idx = d, i
    if dmax <= tol: return [a, b]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


body = urllib.parse.urlencode({"data": Q}).encode()
data = None
for i in range(4):
    try:
        with urllib.request.urlopen(urllib.request.Request(URL, data=body, headers=UA), timeout=700) as r:
            data = json.load(r); break
    except Exception as e:
        print("ponawiam:", e); time.sleep(30 * (i + 1))
if data is None:
    raise SystemExit("OpenHistoricalMap nie odpowiada")

rings = load_poly()
out = []
for w in data.get("elements", []):
    t = w.get("tags", {})
    s, e = year(t.get("start_date")), year(t.get("end_date"))
    if not ((s is not None and s <= 1900) or (e is not None and e <= 1950)):
        continue
    pts = [(round(g["lat"], 5), round(g["lon"], 5)) for g in w.get("geometry", []) if g]
    if len(pts) < 2 or not any(inside(p[0], p[1], rings) for p in pts[::max(1, len(pts) // 5)] + [pts[-1]]):
        continue
    out.append({"id": w["id"], "n": t.get("name", ""), "s": t.get("start_date", ""), "e": t.get("end_date", ""),
                "h": t.get("highway", ""), "src": (t.get("source") or "")[:80], "c": [list(p) for p in simplify(pts)]})

if len(out) < 100:
    raise SystemExit(f"Podejrzanie mało dróg: {len(out)}")
with open("data/drogi_ohm.json", "w", encoding="utf-8") as f:
    json.dump({"generated": datetime.date.today().isoformat(), "count": len(out), "elements": out}, f,
              ensure_ascii=False, separators=(",", ":"))
print("drogi z OpenHistoricalMap:", len(out))
