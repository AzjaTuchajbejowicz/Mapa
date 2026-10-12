"""Zbiera z polskiej Wikipedii miejscowości, w których artykułach jest wzmianka o młynie,
wiatraku, grodzisku, kurhanie albo cmentarzysku. Wynik: build/wzm_mlyny.json, build/wzm_stanowiska.json."""
import json, re, time, urllib.parse, urllib.request

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


MODERN = re.compile(r"restaurac|hotel|pizzer|elektrowni wiatrow|turbin|farm[aęy] wiatrow|wiatraków? energ|młyn(ek)? do kawy|film|serial|piosenk|album|zespół muzyczny", re.I)
DROP = re.compile(r"^(Muzeum|Skansen|Park Etnograficzny|Kalendarium|Lista |Gmina |Powiat |Województwo |\d)")
LAYERS = {
    "mlyny": {
        "queries": ['"młyn wodny"', '"był młyn"', '"znajdował się młyn"', '"młyn i karczma"', '"karczma i młyn"', '"młyny wodne"',
                    '"dwa młyny"', '"młyn zbożowy"', '"młyn"', '"wiatrak"', '"wiatraki"', '"wiatrak koźlak"', '"holender"',
                    '"młynem"', '"młyna"', '"młynie"', 'młyn wodny', 'wiatrak koźlak', 'młyn'],
        "hit": re.compile(r"(?<![A-ZĄĆĘŁŃÓŚŹŻ])\b(młyn|wiatrak|koźlak|paltrak|folusz)"),
    },
    "stanowiska": {
        "queries": ['"grodzisko"', '"grodziska"', '"kurhan"', '"kurhany"', '"cmentarzysko"', '"stanowisko archeologiczne"',
                    '"osada kultury"', '"ślady osadnictwa"', '"grodzisko stożkowate"', '"grodzisko pierścieniowate"',
                    '"cmentarzysko kurhanowe"', '"cmentarzysko ciałopalne"', 'grodzisko wczesnośredniowieczne',
                    'cmentarzysko kultury łużyckiej', 'kurhan', 'grodzisko'],
        "hit": re.compile(r"(?<![A-ZĄĆĘŁŃÓŚŹŻ])\b(grodzisk|kurhan|cmentarzysk|stanowisk\w* archeolog|osad\w* kultury|ślady osadnictwa|gród)"),
    },
}

for layer, cfg in LAYERS.items():
    found = {}
    for q in cfg["queries"]:
        off = 0
        while off is not None and off < 9500:
            d = wiki(action="query", list="search", srnamespace=0, srlimit=500, srprop="snippet", sroffset=off, srsearch=q)
            for x in d.get("query", {}).get("search", []):
                sn = re.sub(r"<[^>]+>", "", x["snippet"]).replace("&quot;", '"').replace("&#039;", "'")
                if cfg["hit"].search(sn) and not MODERN.search(sn) and x["title"] not in found and not DROP.search(x["title"]):
                    found[x["title"]] = re.sub(r"\s+", " ", sn).strip()
            off = d.get("continue", {}).get("sroffset")
            time.sleep(0.2)
    print(layer, "artykuły z wzmianką:", len(found))
    items, titles = [], list(found)
    for i in range(0, len(titles), 50):
        d = wiki(action="query", prop="coordinates", colimit="max", redirects=1, titles="|".join(titles[i:i + 50]))
        q = d.get("query", {})
        back = {n["to"]: n["from"] for n in q.get("normalized", []) + q.get("redirects", [])}
        for p in q.get("pages", []):
            if not p.get("coordinates"):
                continue
            c = p["coordinates"][0]
            t = back.get(p["title"], p["title"])
            if not (49.0 < c["lat"] < 54.9 and 14.1 < c["lon"] < 24.2):
                continue
            sn = found.get(t, "")
            if re.search(r"https?://|ISAP|\[dostęp", sn):
                sn = ""
            items.append({"title": t, "place": re.sub(r" \(.*\)$", "", t), "lat": round(c["lat"], 5), "lon": round(c["lon"], 5), "text": sn[:260]})
        time.sleep(0.2)
    with open(f"build/wzm_{layer}.json", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, separators=(",", ":"))
    print(layer, "ze współrzędnymi:", len(items))
