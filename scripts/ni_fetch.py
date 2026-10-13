#!/usr/bin/env python3
"""Nicaragua: "Normas Jurídicas de Nicaragua" database of the Asamblea Nacional
(Dirección de Información Legislativa, http://legislacion.asamblea.gob.ni/normaweb.nsf).
The Lotus Domino view "NJPublicadas" (categorised by type of norm) is read with
?ReadViewEntries (XML); each document is fetched as HTML (?OpenDocument).

Usage: ni_fetch.py [list|docs|convert|all]
"""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date
from urllib.parse import quote

import requests
import yaml
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ni_textmd as T  # noqa: E402

RAW = os.environ.get("RAW", "/Users/magicaltux/projects/lawcodex/_raw/ni")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
DB = "http://legislacion.asamblea.gob.ni/normaweb.nsf"
VIEW = DB + "/9e314815a08d4a6206257265005d21f9"
TODAY = date.today().isoformat()
CATS = {"Constituciones Políticas de Nicaragua": ("constituciones", "constitution"),
        "Códigos": ("codigos", "code"), "Leyes": ("leyes", "act"),
        "Decretos - Ley": ("decretos-ley", "decree-law"), "Decretos Legislativos": ("decretos-legislativos", "legislative-decree"),
        "Acuerdo Legislativo": ("acuerdos-legislativos", "legislative-act"), "Reglamentos": ("reglamentos", "regulation")}
s = requests.Session()
s.headers["User-Agent"] = UA
_last = [0.0]


def get(url):
    for k in range(5):
        w = 1.0 - (time.time() - _last[0])
        if w > 0:
            time.sleep(w)
        _last[0] = time.time()
        try:
            r = s.get(url, timeout=(30, 600))
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
            print("HTTP", r.status_code, url, file=sys.stderr, flush=True)
        except requests.RequestException as e:
            print("ERR", url, e, file=sys.stderr, flush=True)
        time.sleep(15 * (k + 1))
    return None


def slug(t, n=80):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:n].rstrip("-")


def build_list():
    rows = []
    for cat in CATS:
        start = "1"
        seen_pos = set()
        while True:
            x = get(f"{VIEW}?ReadViewEntries&RestrictToCategory={quote(cat)}&ExpandView&Start={start}&Count=500")
            t = x.decode("utf-8", "replace") if x else ""
            allpos = re.findall(r'<viewentry position="([\d.]+)"', t)
            new = 0
            for pos, unid, body in re.findall(r'<viewentry position="([\d.]+)"[^>]*unid="([0-9A-F]+)"[^>]*>(.*?)</viewentry>', t, re.S):
                if pos in seen_pos:
                    continue
                seen_pos.add(pos)
                new += 1
                cols = dict(re.findall(r'name="([^"]+)"[^>]*>\s*<(?:text|number|datetime)>([^<]*)<', body))
                rows.append({"cat": cat, "unid": unid, "fecha": cols.get("NJFechaPublicacion", "")[:8],
                             "numero": cols.get("NJNumeroLD", ""), "titulo": cols.get("NJTitulo", "").strip()})
            if len(allpos) < 500 or allpos[-1] == start:
                break
            start = allpos[-1]  # categorised views page by position ("7.75"), first row repeats
        print(cat, sum(1 for r in rows if r["cat"] == cat), flush=True)
    seen = set()
    rows = [r for r in rows if not (r["unid"] in seen or seen.add(r["unid"]))]
    json.dump(rows, open(os.path.join(RAW, "list.json"), "w"), ensure_ascii=False, indent=0)
    print("total", len(rows))


def docs(workers=3):
    """Document pages; up to 3 parallel connections, each paced at 1 request/s."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    d = os.path.join(RAW, "docs")
    os.makedirs(d, exist_ok=True)
    rows = json.load(open(os.path.join(RAW, "list.json")))
    local = threading.local()

    def worker(r):
        p = os.path.join(d, r["unid"] + ".html")
        if os.path.exists(p):
            return
        if not hasattr(local, "s"):
            local.s = requests.Session()
            local.s.headers["User-Agent"] = UA
            local.last = 0.0
        for k in range(5):
            w = 1.0 - (time.time() - local.last)
            if w > 0:
                time.sleep(w)
            local.last = time.time()
            try:
                x = local.s.get(f"{DB}/($All)/{r['unid']}?OpenDocument", timeout=(30, 600))
                if x.status_code == 200:
                    open(p, "wb").write(x.content)
                    return
                if x.status_code == 404:
                    return
            except requests.RequestException as e:
                print("ERR", r["unid"], e, file=sys.stderr, flush=True)
            time.sleep(15 * (k + 1))

    n = 0
    with ThreadPoolExecutor(workers) as ex:
        for _ in ex.map(worker, rows):
            n += 1
            if n % 500 == 0:
                print("docs", n, len(rows), flush=True)


def doc_lines(raw):
    try:
        h = raw.decode("utf-8")
    except UnicodeDecodeError:
        h = raw.decode("latin-1")
    soup = BeautifulSoup(h, "lxml")
    for t in soup(["script", "style", "head"]):
        t.decompose()
    lines = [re.sub(r"\s+", " ", l).strip() for l in soup.get_text("\n").split("\n")]
    lines = [l for l in lines if l]
    # header: "... Normas Jurídicas ... Categoría normativa: X Materia: Y" ; footer: Asamblea address block
    start = 0
    for i, l in enumerate(lines[:60]):
        if l.startswith("Materia:"):
            start = i + 1 if l.strip() != "Materia:" else i + 2
            break
    if start < len(lines) and lines[start].startswith("Enlace a última versión"):
        start += 1
    end = len(lines)
    for i in range(len(lines) - 1, max(0, len(lines) - 25), -1):
        if lines[i].startswith("Asamblea Nacional de la República de Nicaragua"):
            end = i
            break
    body = lines[start:end]
    while body and body[-1] in ("-", "."):
        body.pop()
    a = soup.find("a", string=re.compile("última versión"))
    latest = a["href"] if a and a.get("href") else None
    return body, latest


def convert():
    st = {}
    used = set()
    for r in json.load(open(os.path.join(RAW, "list.json"))):
        p = os.path.join(RAW, "docs", r["unid"] + ".html")
        if not os.path.exists(p):
            continue
        body, latest = doc_lines(open(p, "rb").read())
        if len(" ".join(body)) < 80:
            st["empty"] = st.get("empty", 0) + 1
            continue
        folder, typ = CATS[r["cat"]]
        f = r["fecha"]
        iso = f"{f[:4]}-{f[4:6]}-{f[6:8]}" if re.fullmatch(r"\d{8}", f) else None
        year = f[:4] if iso else "sin-fecha"
        title = r["titulo"] or (body[0][:200] if body else r["unid"])
        num = r["numero"] if r["numero"] not in ("", "S/N", "-") else None
        base = f"{slug(num, 20)}-" if num else ""
        sub = "" if folder in ("constituciones", "codigos") else f"{year}/"
        fn = f"{folder}/{sub}{year}-{base}{slug(title, 60)}.md"
        k = 2
        while fn in used:
            fn = re.sub(r"(-v\d+)?\.md$", f"-v{k}.md", fn)
            k += 1
        used.add(fn)
        md = T.blocks_to_md(body)
        label = {"leyes": "Ley", "decretos-ley": "Decreto-Ley", "decretos-legislativos": "Decreto Legislativo",
                 "codigos": "Código", "reglamentos": "Reglamento", "acuerdos-legislativos": "Acuerdo Legislativo"}.get(folder)
        front = {"title": title, "identifier": f"{label} N° {num}" if (num and label) else None, "type": typ,
                 "jurisdiction": "ni", "language": "es", "date": iso, "status": "unknown",
                 "source": f"{DB}/($All)/{r['unid']}?OpenDocument", "latest_version": latest, "retrieved": TODAY}
        fm = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, width=1000).strip()
        path = os.path.join(REPO, fn)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write("\n".join(["---", fm, "---", "", f"# {title}", "",
            f"> Normas Jurídicas de Nicaragua (Asamblea Nacional) — {r['cat']}.", "", md, ""]))
        st[folder] = st.get(folder, 0) + 1
    print(st)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("list", "all"):
        build_list()
    if cmd in ("docs", "all"):
        docs()
    if cmd in ("convert", "all"):
        convert()
