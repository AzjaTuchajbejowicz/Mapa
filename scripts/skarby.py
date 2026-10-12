"""Buduje data/skarby.json: udokumentowane znaleziska skarbów w Polsce.

Źródła: polska Wikipedia (artykuły o skarbach i wzmianki o znalezionych skarbach
w artykułach o miejscowościach) oraz Wikidata. Uruchamiane przez GitHub Actions."""
import json, re, time, datetime, urllib.parse, urllib.request

UA = {"User-Agent": "mapa-detektorysty/1.0 (https://github.com/AzjaTuchajbejowicz/Mapa)"}
API = "https://pl.wikipedia.org/w/api.php"


def get(url, params=None, tries=4):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print("  ponawiam:", e)
            time.sleep(5 * (i + 1))
    raise SystemExit("Nie udało się pobrać: " + url)


def wiki(**p):
    p.update(format="json", formatversion="2")
    return get(API, p)


def in_pl(lat, lon):
    return 49.0 < lat < 54.9 and 14.1 < lon < 24.2


# 1. Wzmianki o znalezionych skarbach w artykułach (głównie o miejscowościach)
QUERIES = ['"znaleziono skarb"', '"odkryto skarb"', '"skarb monet"', '"skarb denarów"', '"skarb srebrny"',
           '"skarb brązowy"', '"skarb przedmiotów"', '"skarb ozdób"', '"skarbu monet"', '"skarb złotych"',
           '"natrafiono na skarb"', '"wykopano skarb"', '"skarb z okresu"', '"skarb z epoki"',
           'skarb monet', 'skarb denarów', 'skarb srebrny', 'skarb brązowy', 'skarb ozdób', 'skarb siekier',
           'skarb bransolet', 'skarb rzymskich monet', 'skarb wczesnośredniowieczny', 'skarb halsztacki',
           'skarb monet srebrnych', 'skarb monet złotych', 'skarb przedmiotów brązowych', 'skarb ze srebra',
           'skarb siekańców', 'skarb dirhemów', 'skarb groszy', 'skarb talarów', 'znaleziono skarb', 'odkryto skarb',
           'skarb kultury łużyckiej', 'skarb z epoki brązu', 'skarb z okresu wpływów rzymskich', 'depozyt brązowy',
           'skarb monet średniowiecznych', 'skarb monet z XVII', 'skarbu monet']
GOOD = re.compile(r"((znalezion|odkryt|natrafion|wykopan|wyoran|odnalezion|wydobyt)\w*[^.]{0,40}skarb\w*[^.]{0,60}"
                  r"|skarb\w*\s[^.]{0,25}(monet|denar|srebr|brąz|złot|ozdób|siekier|bransolet|naszyjnik|dirhem|grosz|"
                  r"talar|szeląg|halszt|łużyck|rzymsk|wczesnośredn|przedmiot|bursztyn|sierp|epoki|okresu|dukat|krzyżack)[^.]{0,60})",
                  re.I)
BAD = re.compile(r"Skarb\w* Państwa|skarbnik|skarbc|skarbow|Skarb\w* Kości|skarb\w* narodow|skarbiec|Skarb\w* Koronn|Skarb\w* Rzesz", re.I)
# artykuły, w których wzmianka nie wskazuje miejsca znaleziska (muzea, legendy, ogólniki)
DROP = re.compile(r"^(Muzeum|Skarb |Chmielewo Małe|Wolin \(wyspa\)|Woliński Park|Zubowe Skały|Bracia Łopieńscy|Kościół św\. Krzyża|"
                  r"Biezdrowo|Prudnik|Czerwionka|Sobięcin|Liptovská|Lębork|Warnowo|Kapliczka Bulandy|Bularka|Jadowskie|Klęcino|"
                  r"Grądy|Zielonki|Pałac w Strudze|Dom Jana z Dziekanowic|Kalendarium|\d)")

found = {}
for q in QUERIES:
    off = 0
    while off is not None and off < 2000:
        d = wiki(action="query", list="search", srnamespace=0, srlimit=500, srprop="snippet", sroffset=off, srsearch=q)
        for x in d.get("query", {}).get("search", []):
            sn = re.sub(r"<[^>]+>", "", x["snippet"])
            m = GOOD.search(sn)
            if m and not BAD.search(m.group(0)) and x["title"] not in found:
                found[x["title"]] = sn
        off = d.get("continue", {}).get("sroffset")
        time.sleep(0.3)
print("wzmianki:", len(found))


def coords_for(titles):
    out = {}
    titles = list(titles)
    for i in range(0, len(titles), 50):
        d = wiki(action="query", prop="coordinates", colimit="max", redirects=1, titles="|".join(titles[i:i + 50]))
        q = d.get("query", {})
        back = {n["to"]: n["from"] for n in q.get("normalized", []) + q.get("redirects", [])}
        for p in q.get("pages", []):
            if p.get("coordinates"):
                c = p["coordinates"][0]
                out[back.get(p["title"], p["title"])] = (c["lat"], c["lon"])
        time.sleep(0.3)
    return out


def clean(t):
    t = re.sub(r"\[[^\]]*\]", "", t)
    return re.sub(r"\s+", " ", t).replace("&quot;", '"').replace("&#039;", "'").strip()


items = []
co = coords_for(found)
for title, (lat, lon) in co.items():
    if not in_pl(lat, lon) or DROP.search(title):
        continue
    place = re.sub(r" \(.*\)$", "", title)
    t = clean(found[title])
    if re.search(r"https?://|\bs\.\s\d|ISAP|\(pol\.\)|\[dostęp", t):
        t = ""
    items.append({"n": "Skarb – " + place, "p": place, "lat": round(lat, 5), "lon": round(lon, 5), "t": t[:300], "w": title, "a": 0})

# 2. Artykuły o konkretnych skarbach: miejsce znalezienia ze współrzędnych artykułu albo miejscowości
HOARDS = {  # skarb: artykuł o miejscu znalezienia
    "Skarb średzki": "Środa Śląska", "Skarb rodziny Pavelów": "Środa Śląska", "Skarb ze Słuszkowa": "Słuszków",
    "Skarb z Witaszkowa": "Witaszkowo", "Skarb z Czapur": "Czapury", "Skarb z Kiekrza": "Kiekrz",
    "Skarb zakrzowski": "Zakrzów (Wrocław)", "Skarb bursztynu z Basoni": "Basonia",
    "Skarb kotowicki": "Kotowice (powiat wrocławski)", "Skarb z Siedlikowa": "Siedlików", "Skarb ze Skrwilna": "Skrwilno",
    "Skarb bydgoski": "Katedra św. Marcina i Mikołaja w Bydgoszczy", "Skarb oświęcimski": "Wielka Synagoga w Oświęcimiu",
    "Skarb groszy praskich z Oleśnicy": "Oleśnica", "Skarb groszy praskich z Boguszowa": "Boguszów (Boguszów-Gorce)",
    "Skarb żelaznych grzywien": "Dom Jana z Dziekanowic w Krakowie", "Skarb z Zagórzyna": None,
}
FIXED = {  # współrzędne sprawdzone ręcznie; dla pozostałych bierzemy współrzędne artykułu o miejscu
    "Skarb z Zagórzyna": (51.81411, 18.03369), "Skarb z Czapur": (52.33668, 16.91195), "Skarb z Kiekrza": (52.4789, 16.78329),
    "Skarb z Witaszkowa": (51.8667, 14.7667), "Skarb średzki": (51.16389, 16.595), "Skarb rodziny Pavelów": (51.16417, 16.5925),
    "Skarb ze Słuszkowa": (51.93347, 18.23713), "Skarb bursztynu z Basoni": (51.00389, 21.82583),
    "Skarb kotowicki": (51.02556, 17.22306), "Skarb z Siedlikowa": (51.47833, 17.96111), "Skarb ze Skrwilna": (53.0175, 19.62111),
    "Skarb bydgoski": (53.12285, 17.99933), "Skarb oświęcimski": (50.039, 19.22), "Skarb groszy praskich z Oleśnicy": (51.20889, 17.38556),
    "Skarb groszy praskich z Boguszowa": (50.75278, 16.2025), "Skarb żelaznych grzywien": (50.05656, 19.93733),
}
pc = coords_for([v for k, v in HOARDS.items() if v and k not in FIXED])
d = wiki(action="query", prop="extracts", exintro=1, explaintext=1, exsentences=3, exlimit=20, titles="|".join(HOARDS))
intro = {p["title"]: p.get("extract", "") for p in d.get("query", {}).get("pages", [])}
for h, place in HOARDS.items():
    c = FIXED.get(h) or pc.get(place) or ((51.11, 17.0325) if h == "Skarb zakrzowski" else None)
    if not c:
        print("  brak współrzędnych:", h)
        continue
    name = re.sub(r" \(.*\)$", "", place or "Zagórzyn")
    items.append({"n": h, "p": name, "lat": round(c[0], 5), "lon": round(c[1], 5), "t": clean(intro.get(h, ""))[:300], "w": h, "a": 1})

# 3. Skarby opisane tylko w Wikidata
for n, p, lat, lon, q in [("Skarb z Czarnowic", "Czarnowice", 51.90243, 14.77058, "Q1191835"),
                          ("Skarb z Sadzarzewic", "Sadzarzewice", 51.885, 14.66556, "Q1191830"),
                          ("Skarb z Węglin", "Węgliny", 51.82315, 14.71949, "Q1191818")]:
    items.append({"n": n, "p": p, "lat": lat, "lon": lon, "t": "Skarb z wczesnej epoki brązu (Wikidata " + q + ").", "w": "", "a": 1})

# miejscowości, o których jest osobny artykuł o skarbie, pokazuję raz
hoard_places = {i["p"] for i in items if i["a"]}
items = [i for i in items if i["a"] or i["p"] not in hoard_places]
items.sort(key=lambda i: (-i["a"], i["n"]))
if len(items) < 50:
    raise SystemExit(f"Podejrzanie mało skarbów: {len(items)}")
with open("data/skarby.json", "w", encoding="utf-8") as f:
    json.dump({"generated": datetime.date.today().isoformat(), "count": len(items), "elements": items}, f,
              ensure_ascii=False, separators=(",", ":"))
print("skarby:", len(items))
