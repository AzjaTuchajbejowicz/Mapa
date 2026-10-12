"""Pobiera z OpenStreetMap (Overpass) stanowiska archeologiczne i młyny dla całej Polski
i zapisuje je jako pliki JSON w katalogu data/, z których korzysta mapa."""
import json, sys, time, urllib.request, urllib.parse, datetime

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
AREA = 'area["ISO3166-1"="PL"][admin_level=2]->.pl;'
QUERIES = {
    "stanowiska": AREA + '(nwr["historic"~"^(archaeological_site|tumulus)$"](area.pl););out center tags;',
    "mlyny": AREA + '(nwr["man_made"~"^(watermill|windmill)$"](area.pl);'
             'nwr["historic"~"^(mill|watermill|windmill)$"](area.pl);'
             'nwr["building"~"^(watermill|windmill)$"](area.pl);'
             'node["place"~"^(village|hamlet|isolated_dwelling|locality|neighbourhood|quarter|farm)$"]["name"~"[Mm]łyn|[Ww]iatrak"](area.pl););out center tags;',
}
KEEP = {"name", "name:pl", "alt_name", "site_type", "archaeological_site", "fortification_type", "historic",
        "historic:civilization", "historic:period", "historic:era", "start_date", "construction_date",
        "description", "description:pl", "note", "note:pl", "wikipedia", "wikipedia:pl", "wikidata",
        "heritage", "heritage:operator", "ref:nid", "man_made", "building", "historic:building", "ruins",
        "ruins:man_made", "windmill:type", "windmill_type", "place"}

def run(q):
    body = urllib.parse.urlencode({"data": "[out:json][timeout:900];" + q}).encode()
    last = None
    for attempt in range(3):
        for url in ENDPOINTS:
            try:
                req = urllib.request.Request(url, data=body, headers={"User-Agent": "mapa-detektorysty (github.com/AzjaTuchajbejowicz/Mapa)"})
                with urllib.request.urlopen(req, timeout=960) as r:
                    return json.load(r)
            except Exception as e:  # serwer przeciążony albo przekroczony czas
                last = e
                print(f"  {url}: {e}", file=sys.stderr)
        time.sleep(60)
    raise SystemExit(f"Nie udało się pobrać danych: {last}")

for name, q in QUERIES.items():
    print("Pobieram", name)
    data = run(q)
    out = []
    for el in data.get("elements", []):
        lat = el.get("lat", el.get("center", {}).get("lat"))
        lon = el.get("lon", el.get("center", {}).get("lon"))
        if lat is None:
            continue
        tags = {k: v for k, v in (el.get("tags") or {}).items() if k in KEEP}
        out.append({"type": el["type"], "id": el["id"], "lat": round(lat, 6), "lon": round(lon, 6), "tags": tags})
    if len(out) < 100:
        raise SystemExit(f"Podejrzanie mało obiektów w {name}: {len(out)}")
    doc = {"generated": datetime.date.today().isoformat(), "count": len(out), "elements": out}
    with open(f"data/{name}.json", "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  zapisano {len(out)} obiektów")
