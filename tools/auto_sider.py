"""
SOEN 321 - run experiments E1-E4 on the Sider extension automatically, while recording with mitmproxy.
Same approach as tools/auto_merlin.py: Edge is driven over its DevTools protocol, and Sider's chat (a side panel page,
or a chrome-extension:// frame inside the tab) is something we can type into. Test pages are served as
https://soen321.test/ because some extensions do not read http:// pages. A person opens Sider once per session.

Usage (from the project folder):
  .venv\\Scripts\\python.exe tools\\auto_sider.py probe                # first: check the script can see Sider's chat
  .venv\\Scripts\\python.exe tools\\auto_sider.py E1:1 E2:1 E3:1 E4:1   # then the runs (experiment:run number)

Sider's page layout was not known when this was written, so the script finds things by role, not by fixed names:
the extension by its name in the test profile, the chat by a text box inside a chrome-extension:// page or frame,
"answer finished" by the answer no longer changing and no Stop button showing. If a step fails, run `probe` and
read evidence/sider/probe.txt. Two overrides if needed (CSS selectors, set in PowerShell before running):
  $env:SIDER_BOX = "textarea"            the chat text box
  $env:SIDER_NEW_CHAT = "button.new"     the New chat button
  $env:SIDER_PAGE = "0"                  do not click Sider's Summarize (page) button before page questions
"""
import glob, json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
MITM = os.path.join(ROOT, ".venv", "Scripts", "mitmdump.exe")
EDGE_PATHS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
CDP = "http://127.0.0.1:9333"
BASE = "https://soen321.test"
PROFILE = os.path.join(ROOT, "profiles", "sider")
DIR = os.path.join("evidence", "sider")
# Same prompts and form values as tools/auto_copilot.py, tools/auto_merlin.py and the runbook (test_pages/index.html)
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

# The chat box has a hint text ("Ask anything..."); Sider also has a helper textarea without one, which must be skipped.
BOX = os.environ.get("SIDER_BOX") or "textarea[placeholder]:visible, [contenteditable='true']:visible"
NEW_CHAT = os.environ.get("SIDER_NEW_CHAT")
# Sider only reads the page when its Summarize button (the page chip above the text box) is used; typed questions
# alone do not include the page. 1 = click it before page questions (default), 0 = typed questions only.
PAGE_CHIP = os.environ.get("SIDER_PAGE", "1") != "0"
CHIP = "[class*='group/summarize']"
USER_MSG = ".user-input-text"
NEW_CHAT_RX = r"new (chat|conversation|thread)|start (a )?new"
LIMIT_RX = re.compile(r"(daily|usage|query|message|free) (limit|quota)|run out of|out of (credits|queries)|"
                      r"upgrade (to|your plan|now)|insufficient credits|credits? (are|is) (used up|exhausted)", re.I)
MODEL_RX = r"GPT|Gemini|Llama|Mistral|Grok|DeepSeek|Fusion|Kimi|Qwen"

# Run inside Sider's page/frame. Labels = aria-label, title, tooltip and visible text of an element.
JS_LABEL = "e => [e.getAttribute('aria-label'), e.title, e.getAttribute('data-tooltip'), e.getAttribute('placeholder'), (e.innerText||'').slice(0,80)].filter(Boolean).join(' | ')"
# Sider is still answering while a Stop control shows. Only exact labels count: Sider also shows an ad button
# "Don't stop at the answer - use Sider Hand", which must not count as busy.
JS_BUSY = """() => [...document.querySelectorAll('button,[role=button],div,span')].some(e => e.offsetParent !== null &&
  (/^stop( generating| responding)?$/i.test((e.innerText || '').trim()) ||
   /^stop( generating| responding)?$/i.test((e.getAttribute('aria-label') || e.title || '').trim())))"""
JS_MARK = """(rx) => { const r = new RegExp(rx, 'i');
  document.querySelectorAll('[data-soen-mark]').forEach(e => e.removeAttribute('data-soen-mark'));
  for (const e of document.querySelectorAll('button,[role=button],a,[title],[aria-label]')) {
    if (e.offsetParent === null) continue;
    const t = [e.getAttribute('aria-label'), e.title, e.getAttribute('data-tooltip'), e.innerText].join(' ');
    if (r.test(t) && t.length < 200) { e.setAttribute('data-soen-mark', '1'); return t.trim(); } }
  return null; }"""
JS_MODEL = """(rx) => { const r = new RegExp(rx, 'i');
  for (const e of document.querySelectorAll('button,[role=button],[role=combobox],span,div')) {
    const t = (e.innerText || '').trim();
    if (e.offsetParent !== null && t && t.length < 40 && !t.includes('\\n') && r.test(t)) return t; }
  return '?'; }"""
JS_DUMP = """() => [...document.querySelectorAll('textarea,input,[contenteditable=true],button,[role=button],[role=textbox]')]
  .slice(0, 200).map(e => ({tag: e.tagName.toLowerCase(), visible: e.offsetParent !== null, id: e.id,
    cls: (typeof e.className === 'string' ? e.className : '').slice(0, 80), aria: e.getAttribute('aria-label'),
    title: e.title, placeholder: e.getAttribute('placeholder'), text: (e.innerText || '').trim().slice(0, 60)}))"""
# Elements showing the open page's title or "Summarize" (Sider's page chip above the text box)
JS_DUMP_PAGE = """(rx) => [...document.querySelectorAll('*')].filter(e => {
    const t = (e.innerText || '').trim(); return t && t.length < 120 && new RegExp(rx, 'i').test(t) && e.children.length < 6; })
  .slice(0, 40).map(e => ({tag: e.tagName.toLowerCase(), visible: e.offsetParent !== null, id: e.id,
    cls: (typeof e.className === 'string' ? e.className : '').slice(0, 100), role: e.getAttribute('role'),
    aria: e.getAttribute('aria-label'), title: e.title, text: (e.innerText || '').trim().slice(0, 80),
    clickable: getComputedStyle(e).cursor === 'pointer'}))"""


class LimitReached(Exception):
    pass


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


def localized(ext_dir, key, locale):
    """Resolve a __MSG_key__ manifest name from the extension's _locales folder."""
    for loc in (locale, "en", "en_US"):
        try:
            msgs = json.load(open(os.path.join(ext_dir, "_locales", loc, "messages.json"), encoding="utf-8-sig"))
        except Exception:
            continue
        for k, v in msgs.items():
            if k.lower() == key.lower():
                return v.get("message", key)
    return key


def find_extension(profile=PROFILE):
    """(id, version, name, side panel path) of the installed Sider extension, read from its manifest in the profile."""
    manifests = sorted(glob.glob(os.path.join(profile, "*", "Extensions", "*", "*", "manifest.json")),
                       key=os.path.getmtime, reverse=True)
    for mf in manifests:
        try:
            m = json.load(open(mf, encoding="utf-8-sig"))
        except Exception:
            continue
        name = m.get("name", "")
        if name.startswith("__MSG_"):
            name = localized(os.path.dirname(mf), name[6:].rstrip("_"), m.get("default_locale", "en"))
        if re.match(r"\s*sider\b", name, re.I):  # the real Sider ("Sider: Chat with all AI ..."), not lookalikes
            ext_id = os.path.basename(os.path.dirname(os.path.dirname(mf)))
            return ext_id, m.get("version", "?"), name, (m.get("side_panel") or {}).get("default_path")
        if "sider" in name.lower():
            print(f"WARNING: ignoring '{name}' - this is not Sider. Remove it from the test profile.", flush=True)
    return None


def answer_from(text, prompt, before):
    """The answer to `prompt` inside the chat's visible text: everything after the last copy of the prompt, minus the
    lines at the bottom that were already there before the prompt was sent (input box hints, buttons, disclaimers)."""
    all_lines = text.splitlines()
    own = [n for n, l in enumerate(all_lines) if l.strip() == prompt.strip()]  # the user's message is its own line
    if own:
        lines = all_lines[own[-1] + 1:]
    else:
        i = text.rfind(prompt[:40])
        if i < 0:
            return ""
        tail = text[i + len(prompt[:40]):]
        rest = prompt[40:]
        if rest and tail.startswith(rest):
            tail = tail[len(rest):]
        lines = tail.strip().splitlines()
    lines = [l for l in "\n".join(lines).strip().splitlines() if l.strip().lower() != "stop generating"]
    footer = [norm(l) for l in before.strip().splitlines()]
    k = 0
    while k < len(lines) and k < len(footer) and k < 25 and norm(lines[-1 - k]) == footer[-1 - k]:
        k += 1
    return "\n".join(lines[:len(lines) - k]).strip()


def norm(line):
    """A line for footer comparison: number-only lines (Sider's credit counter) all compare equal."""
    s = line.strip()
    return "#" if s.isdigit() else s


def new_text(after, before):
    """What appeared in the chat between two snapshots: `after` minus the lines it shares with `before` at the top
    and at the bottom. Used when there is no typed prompt to look for (a click on Sider's Summarize button)."""
    a, b = after.strip().splitlines(), before.strip().splitlines()
    i = 0
    while i < len(a) and i < len(b) and norm(a[i]) == norm(b[i]):
        i += 1
    j = 0
    while j < len(a) - i and j < len(b) - i and j < 25 and norm(a[-1 - j]) == norm(b[-1 - j]):
        j += 1
    return "\n".join(a[i:len(a) - j]).strip()


def kill_leftovers():
    """Stop mitmdump / http.server processes left by an earlier crashed run (only ours, from .venv)."""
    cmd = ("Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '" + ROOT + "\\.venv\\*' -and "
           "($_.Name -eq 'mitmdump.exe' -or $_.CommandLine -like '*http.server*') -and $_.ProcessId -ne " + str(os.getpid()) +
           " } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(1)


class Session:
    """One Edge window for the whole session (Sider is opened by a person once); a new recording per experiment run."""

    def __init__(self, p):
        self.p = p
        ext = find_extension()
        if not ext:
            raise SystemExit("Sider is not installed in profiles\\sider. First do the setup run:\n"
                             "  powershell -ExecutionPolicy Bypass -File tools\\record.ps1 -Assistant sider -Experiment E0 -Run 1\n"
                             "install Sider from the Edge Add-ons store, sign in with the throwaway account, close the window.")
        self.ext_id, self.version, self.name, self.panel_path = ext
        self.prefix = f"chrome-extension://{self.ext_id}/"
        print(f"Found {self.name} {self.version} (id {self.ext_id}, side panel page: {self.panel_path or 'none'})", flush=True)
        os.makedirs(os.path.join(DIR, "screenshots"), exist_ok=True)
        self.stop_file = os.path.join(ROOT, "tools", ".stop_auto")
        kill_leftovers()
        self.server = subprocess.Popen([PY, "-m", "http.server", "8765", "--bind", "127.0.0.1", "--directory", "test_pages"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
        self.start_mitm(os.path.join(DIR, "_session_setup.flow"))
        try:
            if not any(t.get("url", "").startswith(self.prefix) for t in targets()):
                if cdp_up():  # an Edge from another assistant's session is still open on the debugging port
                    p.chromium.connect_over_cdp(CDP).new_browser_cdp_session().send("Browser.close"); time.sleep(3)
                edge = next(e for e in EDGE_PATHS if os.path.exists(e))
                spki = open(os.path.join("tools", "spki.txt")).read().strip()
                subprocess.Popen([edge, "--user-data-dir=" + PROFILE,
                                  "--proxy-server=http://127.0.0.1:8899", "--proxy-bypass-list=<-loopback>",
                                  "--ignore-certificate-errors-spki-list=" + spki, "--remote-debugging-port=9333",
                                  "--no-first-run", "--no-default-browser-check", BASE + "/open_sider.html"])
                for _ in range(60):
                    if cdp_up(): break
                    time.sleep(1)
            self.connect()
            self.host = None
            if not self.find_ui():
                print(">>> In the Edge window, open Sider's chat (click the Sider icon in the toolbar, or the Sider button "
                      "at the right edge of the page). <<<", flush=True)
                self.wait_for_ui(1800)
            self.host = self.find_host()
            print(f"Sider chat found in {self.ui.url} (tab: {self.host.url}).", flush=True)
            self.stop_mitm()
        except BaseException:  # Ctrl+C or an error while waiting: don't leave the recorder and server running
            self.close(); raise

    def connect(self):
        self.b = self.p.chromium.connect_over_cdp(CDP)
        self.ctx = self.b.contexts[0]

    # ---------- finding Sider's chat ----------
    def find_ui(self):
        """Set self.ui (frame with the chat box) and self.ui_page (its page). Prefers the frame in the current tab."""
        found = []
        for c in self.b.contexts:
            for pg in c.pages:
                if pg.is_closed():
                    continue
                for fr in pg.frames:
                    if not fr.url.startswith(self.prefix):
                        continue
                    try:
                        if fr.locator(BOX).count():
                            found.append((pg, fr))
                    except Exception:
                        pass
        if not found:
            return False
        mine = [x for x in found if self.host is not None and x[0] == self.host]
        side = [x for x in found if x[0].url.startswith(self.prefix)]
        self.ui_page, self.ui = (mine or side or found)[-1]
        return True

    def wait_for_ui(self, seconds):
        for i in range(seconds):
            if self.find_ui():
                return
            if i and i % 10 == 0:
                self.connect()  # pick up side panel pages opened since we connected
            time.sleep(1)
        raise RuntimeError("Sider's chat never appeared (run `auto_sider.py probe` to see what the script can find)")

    def ensure_ui(self):
        """After a navigation an in-page sidebar can be rebuilt or closed: find it again, ask for a click if needed."""
        for _ in range(15):
            if self.find_ui():
                return
            time.sleep(1)
        print(">>> Sider's chat closed. Open it again in the Edge window (same tab). <<<", flush=True)
        self.wait_for_ui(600)

    def side_panel_mode(self):
        return self.ui_page.url.startswith(self.prefix)

    def find_host(self):
        """The tab the experiments load pages in: the page holding Sider's frame, or (side panel) the panel's tab."""
        if not self.side_panel_mode():
            return self.ui_page
        web = [pg for pg in self.ctx.pages if pg.url.startswith(("http://", "https://")) and not pg.is_closed()]
        if "tabId=" in self.ui.url:  # panel bound to one tab (as Merlin's is)
            tid = int(re.search(r"tabId=(\d+)", self.ui.url).group(1))
            url = self.ui.evaluate("(id) => chrome.tabs.get(id).then(t => t.url)", tid)
            web = [pg for pg in web if pg.url == url] or web
        if not web:
            pg = self.ctx.new_page(); pg.goto(BASE + "/index.html"); return pg
        visible = [pg for pg in web if pg.evaluate("() => document.visibilityState") == "visible"]
        return (visible or web)[0]

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
        # Edge is left open on purpose: the next session reuses it without another click.
        if getattr(self, "mitm", None) and self.mitm.poll() is None:
            self.stop_mitm()
        self.server.kill()

    # ---------- one experiment run ----------
    def log(self, s):
        print(s, flush=True); self.t.write(s + "\n"); self.t.flush()

    def begin(self, exp, run):
        self.exp, self.run, self.n = exp, run, 0
        self.flow = os.path.join(DIR, f"{exp}_run{run}.flow")
        if os.path.exists(self.flow):
            raise SystemExit(f"{self.flow} exists - pick another run number")
        self.t = open(os.path.join(DIR, f"{exp}_run{run}_transcript.md"), "w", encoding="utf-8")
        self.start_mitm(self.flow)
        if self.host.is_closed():
            self.host = self.find_host()
        for pg in list(self.ctx.pages):  # clean slate: only the host tab (and a side panel) stays
            if pg is not self.host and pg is not self.ui_page and pg.url.startswith(("http://", "https://")):
                pg.close()
        self.go("index.html")
        self.log(f"# {exp} run {run} (automated, {self.name} {self.version} in Edge, model: {self.model()})\n\n"
                 f"Started {datetime.now():%Y-%m-%d %H:%M:%S}. Recording to {self.flow}. "
                 f"Summarize button before page questions: {'yes' if PAGE_CHIP else 'no'}\n")

    def end(self, note="run by tools/auto_sider.py"):
        time.sleep(3)
        self.stop_mitm()
        size = os.path.getsize(self.flow) // 1024 if os.path.exists(self.flow) else 0
        self.log(f"\nFinished {datetime.now():%H:%M:%S}, recording {size} KB")
        self.t.close()
        with open(os.path.join(DIR, "lab_notes.md"), "a", encoding="utf-8") as f:
            f.write(f"- {datetime.now():%Y-%m-%d %H:%M} | {self.exp} run {self.run} | Edge, Sider {self.version} "
                    f"(automated via DevTools protocol) | {size} KB | notes: {note}\n")

    # ---------- actions ----------
    def go(self, path):
        self.host.goto(BASE + "/" + path); self.host.wait_for_load_state("load"); self.host.bring_to_front(); time.sleep(2)
        self.ensure_ui()
        return self.host

    def ui_text(self):
        return self.ui.evaluate("() => document.body.innerText")

    def busy(self):
        try: return self.ui.evaluate(JS_BUSY)
        except Exception: return False

    def model(self):
        try: return self.ui.evaluate(JS_MODEL, MODEL_RX)
        except Exception: return "?"

    def wait_idle(self, limit=120):
        t0 = time.time()
        while self.busy() and time.time() - t0 < limit:
            time.sleep(1)

    def shot(self, name):
        path = os.path.join(DIR, "screenshots", name)
        if self.side_panel_mode():
            self.ui_page.screenshot(path=path, full_page=True)
        else:
            self.ui_page.screenshot(path=path)
        return path

    def old_messages(self):
        """Visible user messages in Sider's chat (Sider can keep a previous chat in the page, hidden)."""
        try: return self.ui.locator(USER_MSG + ":visible").count()
        except Exception: return 0

    def new_chat(self):
        self.wait_idle()
        if NEW_CHAT and self.old_messages():
            self.ui.locator(NEW_CHAT).first.click(); time.sleep(2)
        while self.old_messages():
            ans = input(f">>> Sider's chat still shows {self.old_messages()} of your earlier message(s). Click Sider's "
                        "New chat button in the Edge window, then press Enter here (or type ok and Enter if the chat "
                        "is empty now). <<< ")
            time.sleep(1); self.ensure_ui()
            if ans.strip().lower() == "ok":
                break
        self.log("_(new chat)_\n")

    def wait_answer(self, extract, sent):
        """Done = the answer has text, no Stop button is showing, and the answer is unchanged for 4 s.
        Fallback: unchanged for 20 s (a busy indicator that never goes away). Limit 4 min."""
        last, stable = None, 0
        while time.time() - sent < 240:
            time.sleep(1)
            try:
                a = extract(self.ui_text())
            except Exception:
                self.ensure_ui(); continue
            stable = stable + 1 if a == last else 0
            last = a
            if a and ((stable >= 4 and not self.busy()) or stable >= 20):
                break
        time.sleep(1)
        return extract(self.ui_text())

    def record(self, label, sent, what, answer):
        self.n += 1
        self.shot(f"{self.exp}_run{self.run}_{self.n:02d}_{label}.png")
        self.log(f"## {self.n}. [{label}] tab: {self.host.url.rsplit('/', 1)[-1]} | {datetime.now():%H:%M:%S} ({time.time()-sent:.0f}s)\n\n"
                 f"{what}\n\n**Sider:**\n\n{answer or '(no answer captured - see the screenshot)'}\n")
        if len(answer) < 400 and LIMIT_RX.search(answer):
            raise LimitReached(answer)

    def summarize(self, label):
        """Click Sider's Summarize button on the page chip: the way a Sider user has it read the open page."""
        if not PAGE_CHIP:
            return
        self.host.bring_to_front(); time.sleep(1.5)
        self.ensure_ui(); self.wait_idle()
        chip = self.ui.locator(CHIP).first
        try:
            chip.wait_for(state="visible", timeout=15000)
        except Exception:
            self.shot(f"{self.exp}_run{self.run}_NO_CHIP.png")
            self.log(f"_(Summarize button not shown on {self.host.url.rsplit('/', 1)[-1]}; skipped)_\n"); return
        before = self.ui_text()
        chip.click(); sent = time.time()
        answer = self.wait_answer(lambda txt: new_text(txt, before), sent)
        self.record(label, sent, "**Action:** clicked Sider's **Summarize** button (page chip)", answer)

    def ask(self, prompt, label):
        self.host.bring_to_front(); time.sleep(1.5)
        self.ensure_ui()
        self.wait_idle()
        before = self.ui_text()
        box = self.ui.locator(BOX).last
        box.click(); box.fill(prompt); time.sleep(0.3)
        for attempt in range(60):
            box.press("Enter"); time.sleep(1)
            try:
                if self.ui.locator(BOX).last.evaluate("e => (e.value ?? e.innerText).trim()") == "":
                    break
            except Exception:
                break  # the box was replaced while sending
            if attempt == 0: print("  (prompt not sent yet - retrying)", flush=True)
        else:
            self.shot(f"{self.exp}_run{self.run}_ERROR.png")
            raise RuntimeError("Sider did not accept the prompt after 60 s")
        sent = time.time()
        answer = self.wait_answer(lambda txt: answer_from(txt, prompt, before), sent)
        self.record(label, sent, f"**Prompt:** {prompt}", answer)

    # ---------- experiments (same prompts and pages as the Copilot and Merlin runs) ----------
    def E1(self):
        self.go("e1_article.html"); self.new_chat()
        self.summarize("article_summarize"); self.ask(PROMPTS["E1"]["article"], "article")
        f = self.go("e1_form.html")
        for sel, val in FORM.items(): f.locator(sel).click(); f.locator(sel).type(val, delay=20)
        self.summarize("form_summarize"); self.ask(PROMPTS["E1"]["form"], "form")
        self.go("e1_health.html"); self.summarize("health_summarize"); self.ask(PROMPTS["E1"]["health"], "health")

    def E2(self):
        # Blank page: an assistant that reads the open tab would otherwise read the runbook, which lists the persona.
        self.go("e2_neutral.html"); self.new_chat()
        for i, q in enumerate(PROMPTS["E2_leak"], 1): self.ask(q, f"leak{i}")
        for i, q in enumerate(PROMPTS["E2_test"], 1): self.ask(q, f"samechat_q{i}")
        self.go("e2_neutral.html"); self.new_chat()
        for i, q in enumerate(PROMPTS["E2_test"], 1): self.ask(q, f"newchat_q{i}")

    def E3(self):
        self.wait_idle()
        self.log(f"Part 1 (no Sider use, chat open) starts {datetime.now():%H:%M:%S}\n")
        lp = self.go("e3_long.html")
        lp.evaluate("window.scrollTo(0, document.body.scrollHeight)"); time.sleep(30)
        self.go("e1_article.html"); time.sleep(30)
        self.log(f"Part 2 (Sider used) starts {datetime.now():%H:%M:%S}\n")
        self.go("e3_long.html"); self.new_chat(); self.summarize("longpage_summarize"); self.ask(PROMPTS["E3"], "longpage")

    def E4(self):
        b = self.ctx.new_page(); b.goto(BASE + "/e4_tabB.html"); b.wait_for_load_state("load"); time.sleep(1)
        self.go("e4_tabA.html")  # tab A = the host tab, now in front
        self.new_chat()
        self.summarize("tabA_summarize")
        self.ask(PROMPTS["E4"][0], "tabA_summary"); self.ask(PROMPTS["E4"][1], "tabA_whatelse")

    # ---------- probe: what can the script see? ----------
    def probe(self):
        self.go("e1_article.html")  # a normal page, so Sider shows its page chip
        time.sleep(3)
        L = [f"# Sider probe {datetime.now():%Y-%m-%d %H:%M}", "",
             f"extension: {self.name} {self.version}, id {self.ext_id}, side panel page in manifest: {self.panel_path}",
             f"chat found in: {self.ui.url}", f"  inside page: {self.ui_page.url} (side panel mode: {self.side_panel_mode()})",
             f"host tab: {self.host.url}", f"model shown: {self.model()}", f"busy (Stop button visible): {self.busy()}",
             f"text box selector: {BOX} -> {self.ui.locator(BOX).count()} match(es)"]
        mark = self.ui.evaluate(JS_MARK, NEW_CHAT_RX)
        L.append(f"New chat button: {mark!r}" + ("" if mark else "  <-- NOT FOUND: set $env:SIDER_NEW_CHAT, or click it by hand when asked"))
        L += ["", "## DevTools targets"] + [f"- {t.get('type')}: {t.get('url', '')[:150]}" for t in targets()]
        L += ["", "## Frames per page"]
        for pg in self.ctx.pages:
            L.append(f"- page {pg.url[:120]}")
            L += [f"  - frame {fr.url[:150]}" for fr in pg.frames[1:]]
        L += ["", "## Inputs and buttons in Sider's chat"]
        L += [f"- {json.dumps(e, ensure_ascii=False)}" for e in self.ui.evaluate(JS_DUMP)]
        L += ["", "## Page chip (elements showing the page title or Summarize)"]
        L += [f"- {json.dumps(e, ensure_ascii=False)}" for e in self.ui.evaluate(JS_DUMP_PAGE, r"Urban gardening|Summari[sz]e|this page|current page")]
        L += ["", "## Visible text of Sider's chat (first 3000 characters)", "", self.ui_text()[:3000]]
        out = os.path.join(DIR, "probe.txt")
        open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
        self.shot("probe.png")
        print("\n".join(L[:12]))
        print(f"\nWrote {out} and {DIR}\\screenshots\\probe.png. Check them for your account email before sharing.")


def main(args):
    with sync_playwright() as p:
        s = Session(p)
        try:
            if args == ["probe"]:
                s.probe(); return
            for exp, run in [(a.split(":")[0], int(a.split(":")[1])) for a in args]:
                s.begin(exp, run)
                note = "run by tools/auto_sider.py"
                try:
                    getattr(s, exp)()
                except LimitReached as e:
                    s.log(f"\nSTOPPED: Sider's usage limit reached: {e}")
                    s.end("INCOMPLETE - usage limit reached; delete this run's files and redo it later"); break
                except Exception as e:
                    s.log(f"\nERROR during experiment: {e!r}")
                    note = f"ERROR {e!r:.120} - check the transcript, redo the run if needed"
                s.end(note)
        finally:
            s.close()


if __name__ == "__main__":
    if len(sys.argv) < 2 or not (sys.argv[1:] == ["probe"] or all(re.fullmatch(r"E[1-4]:\d", a) for a in sys.argv[1:])):
        sys.exit(__doc__)
    main(sys.argv[1:])
