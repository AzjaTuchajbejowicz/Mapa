"""Jednorazowe sprawdzenie budowy pliku PRNG (obiekty fizjograficzne)."""
import json, zipfile, io, urllib.request, collections, openpyxl
u = "https://opendata.geoportal.gov.pl/prng/PRNG_OBIEKTY_FIZJOGRAFICZNE_XLSX.zip"
z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(u, timeout=600).read()))
out = {"files": z.namelist()}
name = [n for n in z.namelist() if n.lower().endswith(".xlsx")][0]
wb = openpyxl.load_workbook(io.BytesIO(z.read(name)), read_only=True)
out["sheets"] = wb.sheetnames
ws = wb[wb.sheetnames[0]]
rows = ws.iter_rows(values_only=True)
head = [str(h) for h in next(rows)]
out["header"] = head
sample, cnt, n = [], {k: collections.Counter() for k in head}, 0
for r in rows:
    n += 1
    if n <= 8: sample.append([str(v) for v in r])
    for k, v in zip(head, r):
        if v is not None and len(cnt[k]) < 5000: cnt[k][str(v)[:60]] += 1
out["rows"] = n
out["sample"] = sample
out["top"] = {k: c.most_common(60) for k, c in cnt.items() if len(c) < 3000}
json.dump(out, open("data/_prng_probe.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
