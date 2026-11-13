"""
SOEN 321 - search Mitmproxy recordings for our fake data and list who received it.

Usage:  python analyze_flows.py <evidence_dir> <markers.csv> <output_dir>
(or just run tools\\analyze.ps1)

evidence_dir has one subfolder per assistant (copilot, sider, merlin, perplexity, dryrun, baseline),
each with .flow files named E<n>_run<r>.flow.  markers.csv has columns: label,value

Writes to output_dir:
  marker_hits.csv  one row per (request, marker) where fake data appeared in something the browser SENT
  domains.csv      every host each assistant contacted, how often, and a first/third-party guess
  summary.txt      the same results in readable form
"""
import base64
import csv
import os
import sys
from collections import Counter, defaultdict
from urllib.parse import unquote, unquote_plus

# Hosts we treat as belonging to each assistant's company (first party). Extend as you learn more.
FIRST_PARTY = {
    "copilot": ["microsoft.com", "bing.com", "msn.com", "live.com", "microsoftonline.com", "azureedge.net",
                "office.com", "office.net", "cloud.microsoft", "static.microsoft", "skype.com", "edge.microsoft.com", "teams.microsoft.com"],
    "sider": ["sider.ai", "vidline.com"],
    "merlin": ["getmerlin.in", "foyer.work"],
    "perplexity": ["perplexity.ai", "pplx.ai"],
}
# Well-known analytics / tracking services (third party).
TRACKERS = ["google-analytics.com", "googletagmanager.com", "doubleclick.net", "googlesyndication.com",
            "mixpanel.com", "segment.io", "segment.com", "amplitude.com", "sentry.io", "hotjar.com",
            "clarity.ms", "facebook.com", "facebook.net", "intercom.io", "posthog.com", "datadoghq.com",
            "statsig.com", "growthbook.io", "launchdarkly.com", "fullstory.com", "heap.io", "branch.io"]
LOCAL = ("127.0.0.1", "localhost")


def matches(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)


def party(assistant, host):
    if host.split(":")[0] in LOCAL:
        return "local test server"
    if matches(host, TRACKERS):
        return "third party (tracker)"
    if matches(host, FIRST_PARTY.get(assistant, [])):
        return "first party"
    return "? check manually"


def variants(text):
    """The text plus decoded forms, so URL-encoded or JSON-escaped markers are still found."""
    out = {text}
    for f in (unquote, unquote_plus):
        try:
            out.add(f(text))
        except Exception:
            pass
    out.add(text.replace("\\u0040", "@").replace("\\/", "/"))
    return [t.lower() for t in out]


def marker_forms(value):
    """The marker plus its base64 form (some assistants base64-encode payloads)."""
    forms = [value.lower()]
    raw = value.encode()
    for k in range(3):  # the marker can start at any byte offset inside a base64 payload
        enc = base64.b64encode(b"\0" * k + raw).decode()
        start, end = -(-k // 3) * 4, (k + len(raw)) // 3 * 4
        if end - start >= 8:
            forms.append(enc[start:end])  # case-sensitive: base64 is case-sensitive
    return forms


def outgoing_parts(flow):
    """(where, text) for everything the browser SENT in one flow."""
    req = flow.request
    yield "url", req.pretty_url
    yield "headers", "\n".join(f"{k}: {v}" for k, v in req.headers.items())
    yield "body", req.get_text(strict=False) or ""
    ws = getattr(flow, "websocket", None)
    if ws:
        for msg in ws.messages:
            if msg.from_client:
                yield "websocket", msg.text if msg.is_text else msg.content.decode("utf-8", "ignore")


def scan_flow(flow, markers):
    """Return [(label, value, where)] for every marker found in what this flow sent."""
    found = []
    for where, text in outgoing_parts(flow):
        if not text:
            continue
        texts = variants(text)
        for label, value in markers:
            plain, *b64 = marker_forms(value)
            if any(plain in t for t in texts) or any(b in text for b in b64):
                found.append((label, value, where))
    return found


def read_flows(path):
    from mitmproxy import http, io
    with open(path, "rb") as f:
        for flow in io.FlowReader(f).stream():
            if isinstance(flow, http.HTTPFlow):
                yield flow


def main(evidence_dir, markers_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(markers_path, newline="", encoding="utf-8-sig") as f:
        markers = [(r["label"].strip(), r["value"].strip()) for r in csv.DictReader(f) if r.get("value", "").strip()]

    hits, domains = [], Counter()
    for assistant in sorted(os.listdir(evidence_dir)):
        folder = os.path.join(evidence_dir, assistant)
        if not os.path.isdir(folder):
            continue
        for name in sorted(n for n in os.listdir(folder) if n.endswith(".flow")):
            try:
                for flow in read_flows(os.path.join(folder, name)):
                    host = flow.request.pretty_host
                    domains[(assistant, host)] += 1
                    for label, value, where in scan_flow(flow, markers):
                        hits.append([assistant, name, host, party(assistant, host), flow.request.method,
                                     flow.request.pretty_url[:300], label, value, where])
            except Exception as e:  # a truncated file should not stop the whole analysis
                print(f"WARNING: could not fully read {assistant}/{name}: {e}")

    baseline_hosts = {h for (a, h) in domains if a == "baseline"}

    with open(os.path.join(out_dir, "marker_hits.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["assistant", "recording", "host", "party", "method", "url", "label", "value", "found_in"])
        w.writerows(hits)

    with open(os.path.join(out_dir, "domains.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["assistant", "host", "requests", "party", "also_seen_without_assistant"])
        for (assistant, host), n in sorted(domains.items()):
            w.writerow([assistant, host, n, party(assistant, host), "yes" if host in baseline_hosts else ""])

    # Readable summary
    lines = []
    by_assistant = defaultdict(list)
    for h in hits:
        by_assistant[h[0]].append(h)
    for assistant in sorted({a for a, _ in domains}):
        n_req = sum(n for (a, _), n in domains.items() if a == assistant)
        n_hosts = sum(1 for (a, _) in domains if a == assistant)
        lines.append(f"== {assistant}: {n_req} requests to {n_hosts} hosts")
        seen = defaultdict(set)
        for _, rec, host, prty, *_rest in by_assistant[assistant]:
            label, where = _rest[-3], _rest[-1]
            seen[(rec, label)].add(f"{host} [{prty}, {where}]")
        if not seen:
            lines.append("   no fake data / markers found in anything sent")
        for (rec, label), dests in sorted(seen.items()):
            lines.append(f"   {rec}: {label} -> " + "; ".join(sorted(dests)))
    text = "\n".join(lines)
    with open(os.path.join(out_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\n{len(hits)} hits. Files written to {out_dir}: marker_hits.csv, domains.csv, summary.txt")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    try:
        import mitmproxy  # noqa: F401
    except ImportError:
        sys.exit("mitmproxy is not installed. Run tools\\setup.ps1 first (or: pip install mitmproxy).")
    main(*sys.argv[1:])
