"""Daily harvester: piezo-relevant EU tenders (TED API) and patents (Patentscope RSS).
Keeps everything ever found in data/*.json and rewrites feeds/*.xml (RSS 2.0) for the Valona Research App.
Standard library only."""
import json, os, re, html, time, urllib.request, datetime as dt
from pathlib import Path
from email.utils import format_datetime, parsedate_to_datetime
from xml.sax.saxutils import escape as e

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
UA = {"User-Agent": "Mozilla/5.0 (feed harvester)", "Content-Type": "application/json"}
TODAY = dt.date.today()
# Own-group applicant names are kept out of the public repo: set them as the OWN_GROUP secret (comma-separated).
OWN = [x.strip().upper() for x in os.environ.get("OWN_GROUP", "").split(",") if x.strip()]

def load(name):
    p = ROOT / "data" / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def save(name, obj):
    (ROOT / "data" / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

def first(v):
    if isinstance(v, dict): return first(v.get("eng") or next(iter(v.values()), ""))
    if isinstance(v, list): return first(v[0]) if v else ""
    return "" if v is None else str(v)

# ---------------- Tenders (EU TED) ----------------
COMP = r"piezo|hydrophon|hydrofon|transduc|transducteur|wandler|przetwornik|traductor|trasduttor|sonda ultra|ultrasound probe|ultraschallsonde|głowic|sonar dom|sonardom|phased array|defektoskop|ultradźwiękow|ultrasonic test|zerstörungsfrei|nanopositi|hexapod|piezoaktor|actuator"
SYS = r"towed array|sonobuoy|torped|submarin|mine hunt|acoustic|side.?scan|UUV|sonar|multibeam|fächerecholot|echolot|ecosonda|subacv|unterwasser|underwater|podwodn|povandenin|ROV\b|AUV|hidrograf|hydrograph|litotri|lithotri|HIFU|focaliz|focused ultrasound|histotrip|shock ?wave|stoßwelle|cohlear|coclear|cochle|implant(e|ul)? auditiv|bone conduction|conducción ósea|ultrahang|ultrazvuk|ultrasonograf|ecógraf|ecograf|ultraschallger|ultrason|ultrasound"
EXCL = r"consumable|fungible|consumibil|kit |service|serwis|mantenimiento|maintenance|wartung|construction|budow|reparaci|repair|insurance|termowizyj|natiivikuva|röntgen|x-ray"

def ted_search(query, page):
    body = json.dumps({"query": query, "limit": 250, "page": page,
        "fields": ["publication-number", "notice-title", "buyer-name", "publication-date", "deadline-receipt-tender-date-lot"]}).encode()
    req = urllib.request.Request("https://api.ted.europa.eu/v3/notices/search", data=body, headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=60))

def segment(text):
    if re.search(r"sonar|hydro|underwater|unterwasser|subacv|podwodn|povandenin|ROV|AUV|UUV|multibeam|echolot|naval|navy|marine|submarin|torped|sonobuoy|towed array|mine (hunt|counter)|defen[cs]e|military|armed forces|bundeswehr|wehrtechn|bwb|ministry of defen|armée|ejército|wojsk|antisub|anti-sub|diver detection|side.?scan", text, re.I): return "Aerospace & Defense"
    if re.search(r"litotri|lithotri|HIFU|focaliz|focused|histotri|shock|cohlear|coclear|cochle|auditiv|ultrahang|ultrazvuk|ecógraf|ecograf|ultrasonograf|ultraschallger|medical|hospital|ultrasound", text, re.I): return "Medical Technology"
    if re.search(r"laborator|research|nanopositi|hexapod|thin film", text, re.I): return "Life Sciences Technology"
    return "Industrial Manufacturing & Measurement"

def harvest_tenders():
    from ad_rules import classify
    store = load("tenders.json")
    days = CFG["tenders"]["lookback_days_daily"] if store else CFG["tenders"]["lookback_days_first_run"]
    since = (TODAY - dt.timedelta(days=days)).strftime("%Y%m%d")
    seen = {v.get("dedupe") for v in store.values()}; new = 0
    for term in CFG["tenders"]["search_terms"]:
        for page in range(1, 4):
            try: d = ted_search(f"FT~({term}) AND publication-date>={since}", page)
            except Exception as ex: print("TED skip", term, ex); break
            for n in d.get("notices", []):
                pn = n["publication-number"]
                if pn in store: continue
                title = first(n.get("notice-title"))
                m = re.match(r"^(.+?)\s+–\s+(.+?)\s+–\s+(.*)$", title)
                country, cat, name = m.groups() if m else ("", "", title)
                c = classify(name + " " + cat)
                if not c: continue
                sub, rel, why = c; buyer = first(n.get("buyer-name"))
                key = name.lower()[:70] + "|" + buyer.lower()[:40]
                if key in seen: continue
                seen.add(key); new += 1
                store[pn] = dict(id=pn, date=n["publication-date"][:10], country=country, category=cat, title=name.strip(), buyer=buyer,
                    deadline=first(n.get("deadline-receipt-tender-date-lot"))[:10], relevance=rel, why=why, segment=sub, dedupe=key,
                    link=f"https://ted.europa.eu/en/notice/-/detail/{pn}")
            if len(d.get("notices", [])) < 250: break
            time.sleep(0.5)
    save("tenders.json", store)
    print(f"Tenders: {new} new, {len(store)} total")
    return store

# ---------------- Patents (Patentscope RSS) ----------------
def score_patent(p):
    """Competitor patents, kept only when they fall into one of the six business fields."""
    apps = p["applicant"].upper(); t = (p["title"] + " " + p["abstract"]).lower()
    comp = next((name for name, keys in CFG["patents"]["competitors"].items() if any(k.upper() in apps for k in keys)), "")
    p["competitor"] = comp
    segs = [s for s, rx in CFG["patents"]["segments"].items() if re.search(rx, t)]
    p["segments"] = segs
    if not comp: return "Low", "Applicant not on the competitor list"
    if not re.search(r"piezo|ultrason|ultrasound|transduc|pzt|ferroelectric|acoustic|actuator", t): return "Low", f"{comp}: not piezo-related"
    core = re.search(r"piezoelectric (ceramic|material|composition|element|layer|film)|lead-free|knn|bnt|pmn|single crystal|multilayer|stack|thin film", t)
    if not segs and not core: return "Low", f"{comp}: piezo patent outside the six business fields"
    why = f"Competitor filing: {comp}" + (f"; field: {', '.join(segs)}" if segs else "")
    if core: return "High", why + "; piezo material or element – core technology"
    return "Medium", why + "; piezo application"

def harvest_patents():
    store = load("patents.json"); new = 0
    for f in CFG["patents"]["rss_feeds"]:
        try:
            xml = urllib.request.urlopen(urllib.request.Request(f["url"], headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "replace")
        except Exception as ex: print("Patent feed skip", f["name"], ex); continue
        for it in re.findall(r"<item>(.*?)</item>", xml, re.S):
            g = lambda tag: [html.unescape(re.sub(r"<[^>]+>", " ", x)).strip() for x in re.findall(rf"<{tag}>(.*?)</{tag}>", it, re.S)]
            link = (g("link") or [""])[0]; pid = (g("guid") or [link.split("docId=")[-1]])[0]
            if not pid or pid in store: continue
            p = dict(id=pid, title=(g("title") or ["(no title)"])[0], link=link,
                     abstract=re.sub(r"\s+", " ", (g("description") or [""])[0]),
                     date=parsedate_to_datetime(g("pubDate")[0]).date().isoformat() if g("pubDate") else TODAY.isoformat(),
                     applicant="; ".join(dict.fromkeys(c for c in g("dc:creator") if re.search(r"[A-Za-z]", c))), feed=f["name"])
            p["relevance"], p["why"] = score_patent(p)
            store[pid] = p; new += 1
    save("patents.json", store)
    print(f"Patents: {new} new, {len(store)} total")
    return store

# ---------------- RSS output ----------------
def write_rss(fn, title, desc, items):
    out = []
    for it in sorted(items, key=lambda x: x["date"], reverse=True)[:1000]:
        d = format_datetime(dt.datetime.fromisoformat(it["date"]).replace(hour=8, tzinfo=dt.timezone.utc), usegmt=True)
        out.append(f'<item><title>{e(it["t"])}</title><link>{e(it["link"])}</link><description>{e(it["d"])}</description>'
                   f'<pubDate>{d}</pubDate><guid isPermaLink="false">{e(it["id"])}</guid>'
                   + "".join(f"<category>{e(c)}</category>" for c in it["cats"]) + "</item>")
    now = format_datetime(dt.datetime.now(dt.timezone.utc), usegmt=True)
    (ROOT / "feeds" / fn).write_text('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        f"<title>{e(title)}</title><link>https://github.com/</link><description>{e(desc)}</description><language>en</language><lastBuildDate>{now}</lastBuildDate>\n"
        + "\n".join(out) + "\n</channel></rss>\n", encoding="utf-8")

def main():
    T = harvest_tenders(); P = harvest_patents()
    write_rss("tenders.xml", "Aerospace & Defense – public tenders (EU TED)",
        "EU public tenders in aerospace, defence, space and astronomy where piezo actuators or transducers are used. High = component level, Medium = system level. Updated daily.",
        [dict(id="TED-" + t["id"], date=t["date"], link=t["link"],
              t=f'Tender – {t["country"]}, {t["category"]}: {t["title"][:200]}',
              d=f'{t["country"]} – {t["category"]}. Buyer: {t["buyer"]}. ' + (f'Deadline: {t["deadline"]}. ' if t["deadline"] else "") + f'Segment: {t["segment"]}. Relevance: {t["relevance"]} – {t["why"]}.',
              cats=["Tenders", t["segment"], "Relevance: " + t["relevance"]]) for t in T.values()])
    write_rss("patents.xml", "Competitor patents – piezo (WIPO Patentscope)",
        "Piezo patents filed by monitored competitors, rated High or Medium relevance. Updated daily.",
        [dict(id=p["id"], date=p["date"], link=p["link"],
              t=f'{p["title"].capitalize() if p["title"].isupper() else p["title"]} ({p["id"]})',
              d=f'{p["abstract"]}\n\nCompetitor: {p.get("competitor") or "n/a"} · Applicant: {p["applicant"] or "n/a"} · Publication: {p["id"]} · Relevance: {p["relevance"]} – {p["why"]}',
              cats=["Patents", "Competitor patents"] + ([p.get("competitor")] if p.get("competitor") else []) + p.get("segments", []) + ["Relevance: " + p["relevance"]]) for p in P.values() if p["relevance"] != "Low"])

if __name__ == "__main__":
    main()
