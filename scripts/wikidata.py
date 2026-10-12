"""Pobiera z Wikidata obiekty w Polsce ze współrzędnymi dla warstw mapy
(stanowiska, młyny, pałace i zamki, karczmy). Wynik: build/wd.json.
Wikidata zawiera m.in. obiekty z rejestru zabytków NID (właściwość P3424)."""
import json, re, time, urllib.parse, urllib.request

UA = {"User-Agent": "mapa-detektorysty/1.0 (https://github.com/AzjaTuchajbejowicz/Mapa)", "Accept": "application/sparql-results+json"}
URL = "https://query.wikidata.org/sparql"

# klasa Wikidata -> (warstwa, tagi w stylu OpenStreetMap, z których korzysta mapa)
CLASSES = {
    "Q839954": ("stanowiska", {"historic": "archaeological_site"}),
    "Q744099": ("stanowiska", {"historic": "archaeological_site", "site_type": "fortification"}),
    "Q105723436": ("stanowiska", {"historic": "archaeological_site", "site_type": "motte"}),
    "Q34023": ("stanowiska", {"historic": "archaeological_site", "site_type": "tumulus"}),
    "Q5737": ("stanowiska", {"historic": "archaeological_site", "site_type": "tumulus"}),
    "Q2593777": ("stanowiska", {"historic": "archaeological_site", "site_type": "necropolis"}),
    "Q185187": ("mlyny", {"man_made": "watermill"}),
    "Q44494": ("mlyny", {"man_made": "watermill"}),
    "Q38720": ("mlyny", {"man_made": "windmill"}),
    "Q23413": ("palace_zamki", {"historic": "castle", "kind": "zamek"}),
    "Q17715832": ("palace_zamki", {"historic": "castle", "kind": "zamek", "ruins": "yes"}),
    "Q16560": ("palace_zamki", {"historic": "castle", "kind": "palac"}),
    "Q4156067": ("palace_zamki", {"historic": "castle", "kind": "palac"}),
    "Q879050": ("palace_zamki", {"historic": "manor", "kind": "dwor"}),
    "Q16974307": ("palace_zamki", {"historic": "manor", "kind": "dwor"}),
    "Q28843623": ("palace_zamki", {"historic": "manor", "kind": "dwor"}),
    "Q9213397": ("palace_zamki", {"historic": "manor", "kind": "dwor"}),
    "Q1802963": ("palace_zamki", {"historic": "manor", "kind": "dwor"}),
    "Q256020": ("karczmy", {"kind": "building"}),
    "Q966002": ("karczmy", {"kind": "building"}),
}

Q = """SELECT ?i ?co ?iLabel ?art ?reg ?inc ?end ?desc ?locLabel WHERE {
  ?i wdt:P31 wd:%s ; wdt:P17 wd:Q36 ; wdt:P625 ?co .
  OPTIONAL { ?art schema:about ?i ; schema:isPartOf <https://pl.wikipedia.org/> }
  OPTIONAL { ?i wdt:P3424 ?reg }
  OPTIONAL { ?i wdt:P571 ?inc }
  OPTIONAL { ?i wdt:P576 ?end }
  OPTIONAL { ?i schema:description ?desc FILTER(lang(?desc) = "pl") }
  OPTIONAL { ?i wdt:P131 ?loc }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "pl,en". }
}"""


def sparql(q):
    url = URL + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:
            print("  ponawiam:", e)
            time.sleep(10 * (i + 1))
    return None


out = {"stanowiska": {}, "mlyny": {}, "palace_zamki": {}, "karczmy": {}}
for cls, (layer, base) in CLASSES.items():
    rows = sparql(Q % cls)
    if rows is None:
        print("pominięto klasę", cls)
        continue
    for b in rows:
        qid = b["i"]["value"].rsplit("/", 1)[1]
        m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", b["co"]["value"])
        if not m or qid in out[layer]:
            continue
        lon, lat = float(m.group(1)), float(m.group(2))
        if not (49.0 < lat < 54.9 and 14.1 < lon < 24.2):
            continue
        tags = dict(base)
        name = b.get("iLabel", {}).get("value", "")
        loc = b.get("locLabel", {}).get("value", "")
        if loc and not re.match(r"^Q\d+$", loc):
            tags["place"] = loc
        if name and name != qid:
            # ogólne nazwy z rejestru („Dwór”, „Zespół pałacowy”) uzupełniam o miejscowość
            if loc and loc not in name and not re.search(r"\s[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]", name):
                name = name + " – " + loc
            tags["name"] = name
        tags["wikidata"] = qid
        tags["src"] = "wikidata"
        if "art" in b:
            tags["wikipedia"] = "pl:" + urllib.parse.unquote(b["art"]["value"].rsplit("/wiki/", 1)[1]).replace("_", " ")
        if "reg" in b:
            tags["heritage"] = "rejestr"; tags["ref:nid"] = b["reg"]["value"]
        if "inc" in b:
            tags["start_date"] = b["inc"]["value"][:4].lstrip("+")
        if "end" in b and layer == "mlyny":
            tags["demolished:" + tags.pop("man_made")] = base["man_made"]
        if "desc" in b:
            tags["description"] = b["desc"]["value"]
        out[layer][qid] = {"type": "wd", "id": qid, "lat": round(lat, 6), "lon": round(lon, 6), "tags": tags}
    print(cls, layer, "razem", len(out[layer]))
    time.sleep(2)

with open("build/wd.json", "w", encoding="utf-8") as f:
    json.dump({k: list(v.values()) for k, v in out.items()}, f, ensure_ascii=False, separators=(",", ":"))
print({k: len(v) for k, v in out.items()})
