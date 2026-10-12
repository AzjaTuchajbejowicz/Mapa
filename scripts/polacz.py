"""Łączy dane z OpenStreetMap, Wikidata i wzmianek z Wikipedii w pliki warstw mapy (data/*.json),
usuwając duplikaty: obiekt z Wikidata albo wzmianka leżące blisko obiektu już na liście są pomijane."""
import json, math, os, re, datetime

def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("brak", path, e)
        return default

def dist(a, b):
    k = math.cos(math.radians(a["lat"]))
    return math.hypot((a["lat"] - b["lat"]) * 111320, (a["lon"] - b["lon"]) * 111320 * k)

class Grid:
    """Szybkie wyszukiwanie sąsiadów: siatka ok. 1 km."""
    def __init__(self): self.c = {}
    def key(self, p): return (int(p["lat"] * 100), int(p["lon"] * 60))
    def add(self, p):
        self.c.setdefault(self.key(p), []).append(p)
    def near(self, p, r):
        ky, kx = self.key(p); n = int(r / 1000) + 1
        for dy in range(-n, n + 1):
            for dx in range(-n, n + 1):
                for q in self.c.get((ky + dy, kx + dx), []):
                    if dist(p, q) <= r: yield q

def merge(osm, wd, mention, r_wd, r_mention, mention_tags):
    g, out = Grid(), []
    for e in osm:
        e["tags"].setdefault("src", "osm"); g.add(e); out.append(e)
    added_wd = 0
    for e in wd:
        twin = next(g.near(e, r_wd), None)
        if twin:  # ten sam obiekt: uzupełnij brakujące informacje w rekordzie z OSM
            for k in ("wikipedia", "wikidata", "heritage", "ref:nid", "start_date", "description"):
                if k in e["tags"] and k not in twin["tags"]: twin["tags"][k] = e["tags"][k]
            if "name" in e["tags"] and "name" not in twin["tags"]: twin["tags"]["name"] = e["tags"]["name"]
            continue
        g.add(e); out.append(e); added_wd += 1
    added_m = 0
    for m in mention:
        if next(g.near(m, r_mention), None):
            continue
        tags = mention_tags(m)
        if tags is None: continue
        tags.update({"src": "wzmianka", "wikipedia": "pl:" + m["title"], "mention": m["text"], "place": m["place"]})
        e = {"type": "wp", "id": m["title"], "lat": m["lat"], "lon": m["lon"], "tags": tags}
        g.add(e); out.append(e); added_m += 1
    return out, added_wd, added_m

def mill_tags(m):
    t = m["text"].lower()
    w = "wiatrak" in t or "koźlak" in t or "paltrak" in t or "holender" in t
    return {"name": ("Wiatrak – " if w else "Młyn – ") + m["place"], "man_made": "windmill" if w else "watermill"}

def site_tags(m):
    t = m["text"].lower()
    st = "fortification" if ("grodzisk" in t or "gród" in t) else "tumulus" if "kurhan" in t else "necropolis" if "cmentarzysk" in t else "settlement"
    return {"name": "Stanowisko – " + m["place"], "historic": "archaeological_site", "site_type": st}

wd = load("build/wd.json", {})
today = datetime.date.today().isoformat()
plan = [
    ("stanowiska", "build/osm_stanowiska.json", 150, 1500, site_tags, "build/wzm_stanowiska.json"),
    ("mlyny", "build/osm_mlyny.json", 250, 1500, mill_tags, "build/wzm_mlyny.json"),
    ("palace_zamki", "build/osm_palace_zamki.json", 300, 0, None, None),
    ("karczmy_osm", "build/osm_karczmy_osm.json", 200, 0, None, None),
]
for name, osm_path, r_wd, r_m, mtags, m_path in plan:
    osm = load(osm_path, {"elements": []})["elements"]
    if not osm:
        print("pomijam", name, "(brak danych OSM)"); continue
    layer_wd = wd.get("karczmy" if name == "karczmy_osm" else name, [])
    mention = load(m_path, []) if m_path else []
    out, a, b = merge(osm, layer_wd, mention, r_wd, r_m, mtags)
    with open(f"data/{name}.json", "w", encoding="utf-8") as f:
        json.dump({"generated": today, "count": len(out), "sources": {"osm": len(osm), "wikidata": a, "wzmianki": b},
                   "elements": out}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{name}: {len(out)} (OSM {len(osm)}, Wikidata +{a}, wzmianki +{b})")
