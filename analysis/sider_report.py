"""
Sider-specific analysis of the .flow recordings (works without mitmproxy installed).
Sider's message format was not known in advance, so this report does not decode one chat format; it searches
everything the browser sent (URL, request body, client-to-server WebSocket messages; gzip/deflate bodies decoded):
  - hosts per run, first party (Sider) vs third party, and Sider's endpoints with how much was sent to each
  - where each marker appeared (host + endpoint)
  - each prompt: which endpoint carried it and the metadata fields sent alongside (time zone, locale, URL, title, ...)
  - page content uploads: the longest text field holding a page marker, shown as sent (text or HTML?)
  - E3: Sider requests during the "no Sider use" period, using the times written in the run's transcript
Usage: python sider_report.py <evidence/sider> <markers.csv> <out.md>
"""
import csv, json, os, re, sys, zlib
from collections import Counter, defaultdict
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tnetstring_reader import flows

FIRST = ("sider.ai", "vidline.com")
TRACKERS = ("google-analytics.com", "googletagmanager.com", "doubleclick.net", "mixpanel.com", "segment.io", "amplitude.com",
            "sentry.io", "hotjar.com", "clarity.ms", "facebook.com", "facebook.net", "intercom.io", "posthog.com",
            "datadoghq.com", "statsig.com", "growthbook.io", "launchdarkly.com", "fullstory.com", "heap.io", "branch.io")
PROMPTS = ["Summarize this page", "What is this form for, and is it filled in correctly?", "Explain my lab results",
           "I just moved to Kitsilano in Vancouver", "I'm turning 67 next month", "As a woman travelling alone",
           "I earn about $250,000 a year", "I'm really into sailing and birdwatching",
           "Recommend a restaurant for dinner tonight.", "What exercise routine would suit me?",
           "Suggest a gift I could buy myself.", "Plan my weekend.", "What car should I buy?",
           "What is this page about? List every section reference you can see.",
           "What else do I have open in my browser right now?"]
# Page markers: text that is only on a test page, so finding it means page content was sent.
PAGE_MARKERS = ("e1_article", "e1_form_ref", "e1_health_ref", "e3_top", "e3_mid", "e3_bottom", "e4_tabA", "e4_tabB")
META_KEY = re.compile(r"time|zone|tz|locale|lang|country|region|city|geo|location|lat|lon|url|title|host|tab|device|platform|"
                      r"os|browser|version|client|user_?agent|screen", re.I)
SECRET_KEY = re.compile(r"token|auth|cookie|secret|password|passwd|session|sign|key|credential|jwt", re.I)


def s(x): return x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "")


def party(h):
    h = h.split(":")[0]
    if h in ("127.0.0.1", "localhost", "soen321.test"): return "local"
    if any(h == d or h.endswith("." + d) for d in FIRST): return "Sider"
    if any(h == d or h.endswith("." + d) for d in TRACKERS): return "THIRD PARTY (tracker)"
    return "THIRD PARTY"


def header(r, name):
    for k, v in r.get("headers") or []:
        if s(k).lower() == name: return s(v).lower()
    return ""


def body_of(r):
    raw = r.get("content") or b""
    if isinstance(raw, str): return raw
    enc = header(r, "content-encoding")
    try:
        if "gzip" in enc: raw = zlib.decompress(raw, 16 + zlib.MAX_WBITS)
        elif "deflate" in enc: raw = zlib.decompress(raw)
        elif "br" in enc:
            import brotli; raw = brotli.decompress(raw)
    except Exception:
        pass
    return s(raw)


def endpoint(r):
    return s(r.get("path")).split("?")[0] or "/"


def sent_parts(f):
    """(kind, text, timestamp) for everything the browser sent in one flow."""
    r = f["request"]
    yield "url", s(r.get("path")), r.get("timestamp_start") or 0
    b = body_of(r)
    if b: yield "body", b, r.get("timestamp_start") or 0
    for m in (f.get("websocket") or {}).get("messages") or []:
        if m[1]: yield "websocket", s(m[2]), m[3] if len(m) > 3 else 0


def strings(obj, path=""):
    """Every (key path, string) in a JSON value; JSON inside strings is opened too."""
    if isinstance(obj, dict):
        for k, v in obj.items(): yield from strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj): yield from strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        t = obj.strip()
        if t[:1] in "{[":
            try: yield from strings(json.loads(t), path); return
            except Exception: pass
        yield path, obj
    elif obj is not None:
        yield path, str(obj)


def parse_json(text):
    """A body or message as JSON; also handles SSE/socket framing with several JSON records."""
    try: return json.loads(text)
    except Exception: pass
    recs = []
    for part in re.split(r"[\x1e\n]+", text):
        part = re.sub(r"^(data:|\d+)", "", part.strip())
        if part[:1] in "{[":
            try: recs.append(json.loads(part))
            except Exception: pass
    return recs or None


def redact(t):
    t = re.sub(r"eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{5,}", "[redacted JWT]", t)
    return re.sub(r"(?i)(bearer\s+)[\w.\-]{16,}", r"\1[redacted]", t)


def e3_window(transcript):
    """Start and end of the "no Sider use" period, from the transcript the script wrote."""
    try: t = open(transcript, encoding="utf-8").read()
    except Exception: return None
    d = re.search(r"Started (\d{4}-\d{2}-\d{2})", t); a = re.search(r"Part 1 .* starts (\d\d:\d\d:\d\d)", t)
    b = re.search(r"Part 2 .* starts (\d\d:\d\d:\d\d)", t)
    if not (d and a and b): return None
    ts = lambda hms: datetime.strptime(f"{d.group(1)} {hms}", "%Y-%m-%d %H:%M:%S").timestamp()
    return ts(a.group(1)), ts(b.group(1))


def run_report(path, markers, window=None):
    hosts = Counter(); eps = defaultdict(lambda: [0, 0]); hits = defaultdict(set); prompts = []; uploads = {}; quiet = []
    by_label = dict(markers)
    for f in flows(path):
        r = f["request"]; h = s(r.get("host")); pty = party(h); ep = endpoint(r)
        hosts[h] += 1
        for kind, text, ts in sent_parts(f):
            if pty == "Sider" and kind != "url":
                eps[(s(r.get("method")) or "WS", h + ep)][0] += 1; eps[(s(r.get("method")) or "WS", h + ep)][1] += len(text)
            low = text.lower()
            found = [lab for lab, val in markers if val.lower() in low]
            for lab in found: hits[lab].add(f"{h}{ep} ({pty}, {kind})")
            page = "soen321.test" in low or bool(found)
            if window and pty == "Sider" and window[0] <= ts < window[1] and (kind != "url" or page):
                quiet.append((ts, h + ep, kind, len(text), page))
            if pty != "Sider" or kind == "url": continue
            data = parse_json(text)
            pairs = list(strings(data)) if data is not None else [("(raw)", text)]
            for p in PROMPTS:
                if p.lower() in low:
                    meta = sorted({f"{k}={v[:80]}" for k, v in pairs if META_KEY.search(k.split(".")[-1])
                                   and not SECRET_KEY.search(k.split(".")[-1]) and len(v) < 300})
                    keys = sorted({k.split(".")[0].split("[")[0] for k, _ in pairs})[:25]
                    prompts.append((p, h + ep, kind, keys, meta[:30]))
                    break
            for k, v in pairs:
                pm = [lab for lab in PAGE_MARKERS if lab in by_label and by_label[lab].lower() in v.lower()]
                if not pm: continue
                key = (pm[0], v[:200])
                if key not in uploads or len(v) > len(uploads[key][2]):
                    prev = uploads.get(key, (None, set()))[1]
                    uploads[key] = (k, prev | {h + ep}, v)
                else:
                    uploads[key][1].add(h + ep)
    return hosts, eps, hits, prompts, uploads, quiet


def looks_like(text):
    tags = len(re.findall(r"</?(div|p|span|h\d|section|a|li|ul|body|html|meta|input)\b", text, re.I))
    return "HTML" if tags > 3 else ("Markdown" if re.search(r"^#{1,6} ", text, re.M) else "plain text")


def main(d, markers_csv, out):
    markers = [(r["label"], r["value"]) for r in csv.DictReader(open(markers_csv, encoding="utf-8-sig")) if r.get("value")]
    L = ["# Sider: analysis of recordings\n", "Generated by `analysis/sider_report.py`. Tokens are redacted; check before sharing.\n"]
    # Experiment runs only: setup runs (E0) contain the test account's sign-in.
    for name in sorted(n for n in os.listdir(d) if re.match(r"E[1-4]_run\d+\.flow$", n)):
        window = e3_window(os.path.join(d, name.replace(".flow", "_transcript.md"))) if name.startswith("E3") else None
        hosts, eps, hits, prompts, uploads, quiet = run_report(os.path.join(d, name), markers, window)
        L.append(f"## {name}\n")
        L.append(f"- {sum(hosts.values())} requests to {len(hosts)} hosts")
        for kind in ("Sider", "THIRD PARTY (tracker)", "THIRD PARTY"):
            hs = sorted(h for h in hosts if party(h) == kind)
            label = {"Sider": "Sider hosts", "THIRD PARTY (tracker)": "known trackers",
                     "THIRD PARTY": "other third-party hosts (includes Edge's own background traffic)"}[kind]
            L.append(f"- {label}: " + (", ".join(f"{h} ({hosts[h]})" for h in hs) if hs else "none"))
        L.append("\n**Sider endpoints (requests or messages, characters sent):**\n")
        for (m, ep), (n, size) in sorted(eps.items(), key=lambda x: -x[1][1])[:25]:
            L.append(f"- {m} {ep}: {n}x, {size:,} chars")
        if name.startswith("E3"):
            L.append("\n**Sider traffic while Sider was not used (E3 part 1):**\n")
            if window is None: L.append("- transcript times not found; check by hand")
            elif not quiet: L.append("- none")
            for ts, ep, kind, size, page in quiet:
                L.append(f"- {datetime.fromtimestamp(ts):%H:%M:%S} {ep} ({kind}, {size} chars)"
                         + (" **contains the page URL or a marker**" if page else ""))
        L.append(f"\n**Prompts sent ({len(prompts)}), with the metadata fields next to them:**\n")
        for p, ep, kind, keys, meta in prompts:
            L.append(f"- \"{p[:70]}\" -> {ep} ({kind}); top-level fields: {', '.join(keys)}")
            if meta: L.append("  - " + redact("; ".join(meta)))
        L.append("\n**Markers found in traffic sent from the browser:**\n")
        for lab, val in markers:
            if lab in hits: L.append(f"- `{lab}` ({val}) -> {', '.join(sorted(hits[lab]))}")
        L.append(f"\n**Page content uploaded to Sider ({len(uploads)} distinct uploads):**\n")
        for (mk, _), (field, where, v) in uploads.items():
            L.append(f"- page with `{mk}`: field `{field}`, {len(v):,} chars, looks like {looks_like(v)}, sent to "
                     f"{', '.join(sorted(where))}\n\n  > " + redact(v[:1200]).replace("\n", " ") + "\n")
        L.append("")
    text = "\n".join(L)
    open(out, "w", encoding="utf-8").write(text)
    print(text[:4000])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:4])
