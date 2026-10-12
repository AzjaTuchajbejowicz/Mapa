"""Buduje data/karczmy_wiki.json: miejscowości, w których według polskiej Wikipedii
istniała karczma, austeria albo zajazd. Uruchamiane przez GitHub Actions."""
import json, re, time, datetime, urllib.parse, urllib.request

UA = {"User-Agent": "mapa-detektorysty/1.0 (https://github.com/AzjaTuchajbejowicz/Mapa)"}
API = "https://pl.wikipedia.org/w/api.php"


def wiki(**p):
    p.update(format="json", formatversion="2")
    url = API + "?" + urllib.parse.urlencode(p)
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print("  ponawiam:", e)
            time.sleep(5 * (i + 1))
    raise SystemExit("Nie udało się pobrać danych z Wikipedii")


QUERIES = ['"była karczma"', '"znajdowała się karczma"', '"karczma i młyn"', '"młyn i karczma"', '"karczmę"',
           '"dwie karczmy"', '"karczma dworska"', '"karczma przydrożna"', '"zabytkowa karczma"', '"drewniana karczma"',
           '"murowana karczma"', '"istniała karczma"', '"austeria"', '"zajazd z XVIII"', '"zajazd z XIX"', '"karczmy"',
           'karczma', 'karczmą', 'karczmie', 'karczm']
HIT = re.compile(r"karczm|austeri|zajazd|krczm", re.I)
MODERN = re.compile(r"restaurac|hotel|pizzer|gastronom|catering|sieć karczem|lokal|festiwal|serial|film|piosenk|album", re.I)
DROP = re.compile(r"^(Muzeum|Skansen|Park Etnograficzny|Sądecki Park|Karczma|Kalendarium|\d)")

found = {}
for q in QUERIES:
    off = 0
    while off is not None and off < 9500:
        d = wiki(action="query", list="search", srnamespace=0, srlimit=500, srprop="snippet", sroffset=off, srsearch=q)
        for x in d.get("query", {}).get("search", []):
            sn = re.sub(r"<[^>]+>", "", x["snippet"]).replace("&quot;", '"').replace("&#039;", "'")
            if HIT.search(sn) and not MODERN.search(sn) and x["title"] not in found:
                found[x["title"]] = re.sub(r"\s+", " ", sn).strip()
        off = d.get("continue", {}).get("sroffset")
        time.sleep(0.2)
print("artykuły z wzmianką:", len(found))

items = []
titles = list(found)
for i in range(0, len(titles), 50):
    d = wiki(action="query", prop="coordinates", colimit="max", redirects=1, titles="|".join(titles[i:i + 50]))
    q = d.get("query", {})
    back = {n["to"]: n["from"] for n in q.get("normalized", []) + q.get("redirects", [])}
    for p in q.get("pages", []):
        if not p.get("coordinates"):
            continue
        c = p["coordinates"][0]
        t = back.get(p["title"], p["title"])
        if not (49.0 < c["lat"] < 54.9 and 14.1 < c["lon"] < 24.2) or DROP.search(t):
            continue
        place = re.sub(r" \(.*\)$", "", t)
        sn = found.get(t, "")
        if re.search(r"https?://|ISAP|\[dostęp", sn):
            sn = ""
        items.append({"n": "Karczma – " + place, "p": place, "lat": round(c["lat"], 5), "lon": round(c["lon"], 5), "t": sn[:260], "w": t})
    time.sleep(0.2)

if len(items) < 200:
    raise SystemExit(f"Podejrzanie mało karczm: {len(items)}")
items.sort(key=lambda i: i["p"])
with open("data/karczmy_wiki.json", "w", encoding="utf-8") as f:
    json.dump({"generated": datetime.date.today().isoformat(), "count": len(items), "elements": items}, f,
              ensure_ascii=False, separators=(",", ":"))
print("karczmy z Wikipedii:", len(items))
