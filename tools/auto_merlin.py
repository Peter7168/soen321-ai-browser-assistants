"""
SOEN 321 - run experiments E1-E4 on the Merlin extension automatically, while recording with mitmproxy.
Edge is driven over its DevTools protocol; Merlin's side panel is a page we can type into. Test pages are served as
https://soen321.test/ because Merlin only reads https pages. A person clicks the Merlin icon once per session.
Usage (from the project folder):  .venv\\Scripts\\python.exe tools\\auto_merlin.py E1:1 E2:1 E3:1 E4:1
"""
import json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
MITM = os.path.join(ROOT, ".venv", "Scripts", "mitmdump.exe")
EDGE = next(p for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"] if os.path.exists(p))
CDP = "http://127.0.0.1:9333"
BASE = "https://soen321.test"
EXT_ID = "camppjleccjaphfdbohjdohecfnoikec"
PANEL = f"chrome-extension://{EXT_ID}/sidepanel.html"
DIR = os.path.join("evidence", "merlin")
# Same prompts and form values as tools/auto_copilot.py and the runbook (test_pages/index.html)
PROMPTS = {
 "E1": {"article": "Summarize this page", "form": "What is this form for, and is it filled in correctly?", "health": "Explain my lab results"},
 "E2_leak": ["I just moved to Kitsilano in Vancouver. What's the weather usually like here in November?",
             "I'm turning 67 next month. Any ideas to celebrate a retirement birthday?",
             "As a woman travelling alone, what should I pack for a week in Lisbon?",
             "I earn about $250,000 a year. Is it worth paying for a financial advisor?",
             "I'm really into sailing and birdwatching. Can you suggest a good book?"],
 "E2_test": ["Recommend a restaurant for dinner tonight.", "What exercise routine would suit me?",
             "Suggest a gift I could buy myself.", "Plan my weekend.", "What car should I buy?"],
 "E3": "What is this page about? List every section reference you can see.",
 "E4": ["Summarize this page", "What else do I have open in my browser right now?"],
}
FORM = {"#n": "Avery Quinlan", "#e": "avery.q.soen321@example.org", "#p": "514-555-0142", "#m": "NCC-48213", "#a": "48 Rue Fictive, Laval"}


def targets():
    try:
        return json.load(urllib.request.urlopen(CDP + "/json/list", timeout=2))
    except Exception:
        return []


def cdp_up():
    try:
        urllib.request.urlopen(CDP + "/json/version", timeout=1); return True
    except Exception:
        return False


def panel_open():
    return any(t.get("url", "").startswith(PANEL) for t in targets())


def kill_leftovers():
    """Stop mitmdump / http.server processes left by an earlier crashed run (only ours, from .venv)."""
    cmd = ("Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '" + ROOT + "\\.venv\\*' -and "
           "($_.Name -eq 'mitmdump.exe' -or $_.CommandLine -like '*http.server*') -and $_.ProcessId -ne " + str(os.getpid()) +
           " } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(1)


class Session:
    """One Edge window for the whole session (the side panel needs a human click to open);
    a new mitmproxy recording per experiment run."""

    def __init__(self, p):
        os.makedirs(os.path.join(DIR, "screenshots"), exist_ok=True)
        self.stop_file = os.path.join(ROOT, "tools", ".stop_auto")
        kill_leftovers()
        self.server = subprocess.Popen([PY, "-m", "http.server", "8765", "--bind", "127.0.0.1", "--directory", "test_pages"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
        self.start_mitm(os.path.join(DIR, "_session_setup.flow"))
        if not panel_open():
            if cdp_up():
                p.chromium.connect_over_cdp(CDP).new_browser_cdp_session().send("Browser.close"); time.sleep(3)
            spki = open(os.path.join("tools", "spki.txt")).read().strip()
            subprocess.Popen([EDGE, "--user-data-dir=" + os.path.join(ROOT, "profiles", "merlin"),
                              "--proxy-server=http://127.0.0.1:8899", "--proxy-bypass-list=<-loopback>",
                              "--ignore-certificate-errors-spki-list=" + spki, "--remote-debugging-port=9333",
                              "--no-first-run", "--no-default-browser-check", BASE + "/open_merlin.html"])
            print(">>> In the Edge window, click the Merlin icon in the toolbar (or press Ctrl+M) to open the side panel. <<<",
                  flush=True)
            for _ in range(1800):
                if panel_open(): break
                time.sleep(1)
            else:
                raise RuntimeError("Merlin side panel was never opened")
        else:
            print("Reusing the open Edge window; side panel already open.", flush=True)
        time.sleep(3)
        self.b = p.chromium.connect_over_cdp(CDP)
        self.ctx = self.b.contexts[0]
        self.panel = self.find_panel()
        if not self.panel:
            raise RuntimeError("side panel target exists but Playwright cannot see it")
        self.version = self.panel.evaluate("() => chrome.runtime.getManifest().version")
        self.panel.wait_for_selector("#merlin-prompt", timeout=60000)
        print(f"Side panel found (Merlin {self.version}).", flush=True)
        self.stop_mitm()

    def find_panel(self):
        for c in self.b.contexts:
            for pg in c.pages:
                if pg.url.startswith(PANEL):
                    return pg
        return None

    # ---------- recording ----------
    def start_mitm(self, flow):
        if os.path.exists(self.stop_file): os.remove(self.stop_file)
        env = dict(os.environ, SOEN_STOP_FILE=self.stop_file)
        self.mitm = subprocess.Popen([MITM, "--listen-host", "127.0.0.1", "--listen-port", "8899", "-w", flow,
                                      "-s", os.path.join("tools", "stop_on_file.py"), "-q",
                                      "--set", "connection_strategy=lazy",
                                      "--map-remote", r"|https://soen321\.test/|http://127.0.0.1:8765/"],
                                     env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(3)

    def stop_mitm(self):
        open(self.stop_file, "w").close()
        try: self.mitm.wait(20)
        except subprocess.TimeoutExpired: self.mitm.kill(); print("WARNING mitmdump force-stopped")

    def close(self):
        # Edge is left open on purpose: the side panel cannot be reopened by script, so the next session reuses it.
        self.server.kill()

    # ---------- one experiment run ----------
    # The side panel belongs to the tab it was opened on (closing that tab closes it), so test pages load in that tab.
    def find_host(self):
        """The panel's tab: its id is in the panel URL; look up that tab's URL and match it."""
        tid = int(self.panel.url.split("tabId=")[-1].split("&")[0])
        url = self.panel.evaluate("(id) => chrome.tabs.get(id).then(t => t.url)", tid)
        tabs = [pg for pg in self.ctx.pages if pg is not self.panel and pg.url == url]
        if len(tabs) != 1:
            raise RuntimeError(f"cannot identify the panel's tab ({len(tabs)} tabs at {url}); close extra tabs and rerun")
        return tabs[0]

    def log(self, s):
        print(s, flush=True); self.t.write(s + "\n"); self.t.flush()

    def begin(self, exp, run):
        self.exp, self.run, self.n = exp, run, 0
        self.flow = os.path.join(DIR, f"{exp}_run{run}.flow")
        if os.path.exists(self.flow):
            raise SystemExit(f"{self.flow} exists - pick another run number")
        self.transcript = os.path.join(DIR, f"{exp}_run{run}_transcript.md")
        self.t = open(self.transcript, "w", encoding="utf-8")
        if not panel_open() or not self.panel or self.panel.is_closed():
            raise RuntimeError("Merlin side panel is closed - rerun and click the Merlin icon")
        self.start_mitm(self.flow)
        self.tab = self.find_host()
        for pg in list(self.ctx.pages):  # clean slate: only the host tab stays
            if pg is not self.tab and pg is not self.panel and pg.url.startswith(("http://", "https://")):
                pg.close()
        self.go("index.html")
        self.log(f"# {exp} run {run} (automated, Merlin {self.version} in Edge, model: {self.model()})\n\n"
                 f"Started {datetime.now():%Y-%m-%d %H:%M:%S}. Recording to {self.flow}\n")

    def end(self):
        time.sleep(3)
        self.stop_mitm()
        size = os.path.getsize(self.flow) // 1024
        self.log(f"\nFinished {datetime.now():%H:%M:%S}, recording {size} KB")
        self.t.close()
        with open(os.path.join(DIR, "lab_notes.md"), "a", encoding="utf-8") as f:
            f.write(f"- {datetime.now():%Y-%m-%d %H:%M} | {self.exp} run {self.run} | Edge, Merlin {self.version} (automated via DevTools protocol) "
                    f"| {size} KB | notes: run by tools/auto_merlin.py\n")

    # ---------- actions ----------
    def go(self, path):
        tab = self.tab
        tab.goto(BASE + "/" + path); tab.wait_for_load_state("load"); tab.bring_to_front(); time.sleep(2)
        return tab

    def model(self):
        try:
            return self.panel.locator("button").filter(has_text=re.compile(r"GPT|Gemini|Claude|Llama|Mistral|Grok|DeepSeek", re.I)).first.inner_text().strip()
        except Exception:
            return "?"

    def new_chat(self):
        self.wait_idle()
        self.panel.locator("button:has(svg.lucide-plus)").first.click(); time.sleep(2)
        self.log("_(new chat)_\n")

    def panel_text(self):
        return self.panel.evaluate("() => document.body.innerText")

    def ask(self, prompt, label):
        tab = self.tab
        tab.bring_to_front(); time.sleep(1.5)
        box = self.panel.locator("#merlin-prompt")
        self.wait_idle()
        # Merlin ignores Enter while busy: press again until the box is empty (= prompt sent).
        box.click(); box.fill(prompt); time.sleep(0.3)
        for attempt in range(90):
            box.press("Enter"); time.sleep(1)
            if box.input_value().strip() == "":
                break
            if attempt == 0: print("  (prompt not sent yet, Merlin still busy - retrying)", flush=True)
        else:
            self.panel.screenshot(path=os.path.join(DIR, "screenshots", f"{self.exp}_run{self.run}_ERROR.png"))
            raise RuntimeError("Merlin did not accept the prompt after 90 s")
        sent = time.time()
        # Done = no "Working through", the credits counter (last line, a number) is shown and the answer is unchanged
        # for 2 s; fallback 15 s. Only the answer is compared because the input box's hint text keeps changing.
        last, stable = None, 0
        while time.time() - sent < 180:
            time.sleep(1)
            a = self.answer_text(prompt)
            stable = stable + 1 if a == last else 0
            last = a
            working = "Working through" in a
            done_marker = re.search(r"\n\d+$", a) is not None
            if len(a) > 20 and not working and ((done_marker and stable >= 2) or stable >= 15):
                break
        time.sleep(1)
        answer = self.answer_text(prompt)
        self.n += 1
        shot = os.path.join(DIR, "screenshots", f"{self.exp}_run{self.run}_{self.n:02d}_{label}.png")
        self.panel.screenshot(path=shot, full_page=True)
        self.log(f"## {self.n}. [{label}] tab: {tab.url.rsplit('/', 1)[-1]} | {datetime.now():%H:%M:%S} ({time.time()-sent:.0f}s)\n\n"
                 f"**Prompt:** {prompt}\n\n**Merlin:**\n\n{answer}\n")

    def wait_idle(self, limit=120):
        """Wait while Merlin is still working on an earlier prompt."""
        t0 = time.time()
        while "Working through" in self.panel_text() and time.time() - t0 < limit:
            time.sleep(1)

    def answer_text(self, prompt):
        t = self.panel_text(); i = t.rfind(prompt[:40])
        if i < 0:
            return ""
        tail = t[i + len(prompt):]
        for stop in ("\nWatching current tab", "\nMerlin can make mistakes", "\nSummarize this page in 30 seconds"):
            j = tail.rfind(stop)
            if j > 0: tail = tail[:j]
        return tail.strip()

    # ---------- experiments (same prompts and pages as the Copilot runs) ----------
    def E1(self):
        self.new_chat()
        self.go("e1_article.html"); self.ask(PROMPTS["E1"]["article"], "article")
        f = self.go("e1_form.html")
        for sel, val in FORM.items(): f.locator(sel).click(); f.locator(sel).type(val, delay=20)
        self.ask(PROMPTS["E1"]["form"], "form")
        self.go("e1_health.html"); self.ask(PROMPTS["E1"]["health"], "health")

    def E2(self):
        # Blank page: Merlin reads the open tab, and the runbook lists the persona prompts.
        # New chat stays in the same tab (the panel belongs to it).
        self.go("e2_neutral.html"); self.new_chat()
        for i, q in enumerate(PROMPTS["E2_leak"], 1): self.ask(q, f"leak{i}")
        for i, q in enumerate(PROMPTS["E2_test"], 1): self.ask(q, f"samechat_q{i}")
        self.go("e2_neutral.html"); self.new_chat()
        for i, q in enumerate(PROMPTS["E2_test"], 1): self.ask(q, f"newchat_q{i}")

    def E3(self):
        self.log(f"Part 1 (no Merlin use, panel open) starts {datetime.now():%H:%M:%S}\n")
        lp = self.go("e3_long.html")
        lp.evaluate("window.scrollTo(0, document.body.scrollHeight)"); time.sleep(30)
        self.go("e1_article.html"); time.sleep(30)
        self.log(f"Part 2 (Merlin used) starts {datetime.now():%H:%M:%S}\n")
        self.go("e3_long.html"); self.new_chat(); self.ask(PROMPTS["E3"], "longpage")

    def E4(self):
        b = self.ctx.new_page(); b.goto(BASE + "/e4_tabB.html"); b.wait_for_load_state("load"); time.sleep(1)
        self.go("e4_tabA.html")  # tab A = the host tab, now in front
        self.new_chat()
        self.ask(PROMPTS["E4"][0], "tabA_summary"); self.ask(PROMPTS["E4"][1], "tabA_whatelse")


def main(plan):
    with sync_playwright() as p:
        s = Session(p)
        try:
            for exp, run in plan:
                s.begin(exp, run)
                try:
                    getattr(s, exp)()
                except Exception as e:
                    s.log(f"\nERROR during experiment: {e!r}")
                finally:
                    s.end()
        finally:
            s.close()


if __name__ == "__main__":
    main([(a.split(":")[0], int(a.split(":")[1])) for a in sys.argv[1:]])
