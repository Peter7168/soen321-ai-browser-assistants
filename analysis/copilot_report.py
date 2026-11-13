"""
Copilot-specific analysis of the .flow recordings (works without mitmproxy installed).
For each run: hosts contacted, third parties, every page-content upload (fetch_browser_content) and what was in it,
where each marker appeared, and what metadata (location, time zone, locale) travelled with the prompts.
Usage: python copilot_report.py <evidence/copilot> <markers.csv> <out.md>
"""
import csv, json, os, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tnetstring_reader import flows

MS = ("microsoft.com", "office.com", "office.net", "cloud.microsoft", "static.microsoft", "bing.com", "msn.com",
      "live.com", "skype.com", "microsoftonline.com", "azureedge.net", "windows.net", "msedge.net", "virtualearth.net", "bingapis.com", "sharepointonline.com")
def s(x): return x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "")
def party(h):
    if h.startswith("127.0.0.1"): return "local"
    return "Microsoft" if any(h == d or h.endswith("." + d) for d in MS) else "THIRD PARTY"

def page_uploads(f):
    """Client->server ChatHub messages that answer fetch_browser_content: yield (url, title, content)."""
    for m in (f.get("websocket") or {}).get("messages") or []:
        if not m[1]: continue
        for rec in s(m[2]).split("\x1e"):
            if "EdgeContextualPlugin" not in rec and "pageContent" not in rec: continue
            try:
                payload = json.loads(json.loads(rec)["result"]["response"]["payload"])
                for item in payload.get("result", []):
                    data = json.loads(item.get("data", "{}"))
                    pc = data.get("pageContent", "")
                    try:
                        pcj = json.loads(pc); text = " | ".join(r.get("snippet", "") for r in pcj.get("results", []))
                    except Exception: text = pc
                    yield data.get("pageUrl"), data.get("pageTitle"), text
            except Exception as e:
                yield None, None, "UNPARSED: " + rec[:300]

def server_requests(f):
    """Server->client invoke_local_plugin calls (what the server asked the browser for)."""
    for m in (f.get("websocket") or {}).get("messages") or []:
        if m[1]: continue
        t = s(m[2])
        if "invoke_local_plugin" in t:
            for rec in t.split("\x1e"):
                if "invoke_local_plugin" in rec:
                    try:
                        inv = json.loads(rec)["arguments"][0]["invocation"]; pl = json.loads(inv["payload"])
                        yield inv.get("local_endpoint"), pl.get("method"), pl.get("params", {})
                    except Exception: yield None, None, rec[:200]

def prompts(f):
    for m in (f.get("websocket") or {}).get("messages") or []:
        if not m[1]: continue
        for rec in s(m[2]).split("\x1e"):
            if '"target":"chat"' not in rec: continue
            try:
                msg = json.loads(rec)["arguments"][0]["message"]
                yield msg.get("text"), msg.get("locationInfo"), msg.get("locale")
            except Exception: pass

def run_report(path, markers):
    hosts = Counter(); hits = defaultdict(set); ups = []; asks = []; ps = []; pre_invoke = []
    for f in flows(path):
        r = f["request"]; h = s(r["host"])
        hosts[h] += 1
        blob = s(r.get("path")) + " " + s(r.get("content"))
        for m in (f.get("websocket") or {}).get("messages") or []:
            if m[1]: blob += " " + s(m[2])
        for label, val in markers:
            if val.lower() in blob.lower(): hits[label].add(f"{h} ({party(h)})")
        ups += list(page_uploads(f)); asks += list(server_requests(f)); ps += list(prompts(f))
    return hosts, hits, ups, asks, ps

def main(d, markers_csv, out):
    markers = [(r["label"], r["value"]) for r in csv.DictReader(open(markers_csv, encoding="utf-8-sig"))]
    L = ["# Copilot in Edge: analysis of recordings\n"]
    for name in sorted(n for n in os.listdir(d) if re.match(r"E[1-4]_run\d+\.flow$", n)):
        hosts, hits, ups, asks, ps = run_report(os.path.join(d, name), markers)
        L.append(f"## {name}\n")
        tp = sorted({h for h in hosts if party(h) == "THIRD PARTY"})
        L.append(f"- {sum(hosts.values())} requests to {len(hosts)} hosts; third-party hosts: {', '.join(tp) if tp else 'none'}")
        L.append(f"- prompts sent: {len(ps)}; server requests for browser content: {len(asks)}; page uploads: {len(ups)}")
        for txt, loc, loc2 in ps[:1]:
            L.append(f"- metadata sent with prompts: locationInfo={json.dumps(loc)}, locale={loc2}")
        for ep, meth, params in asks:
            md = params.get("x-metadata", {}) if isinstance(params, dict) else {}
            L.append(f"- server asked `{meth}` (contentType={params.get('contentType') if isinstance(params, dict) else '?'}, "
                     f"tabidList={params.get('tabidList') if isinstance(params, dict) else '?'}, userLocation={md.get('userLocation')})")
        L.append("\n**Markers found in traffic sent from the browser:**\n")
        for label, val in markers:
            if label in hits: L.append(f"- `{label}` ({val}) -> {', '.join(sorted(hits[label]))}")
        L.append("\n**Page content uploaded to Copilot:**\n")
        for url, title, text in ups:
            L.append(f"- {url} ({title}): {len(text)} chars\n\n  > {text[:1500]}\n")
        L.append("")
    open(out, "w", encoding="utf-8").write("\n".join(L)); print("\n".join(L)[:3000])

if __name__ == "__main__":
    main(*sys.argv[1:4])
