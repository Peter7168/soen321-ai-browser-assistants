# Sider: how to run E1 to E4

Step-by-step for the Sider runs. Everything is run from the project folder in PowerShell, on Windows with Edge.
Expect about 1.5 hours, most of it waiting while the script runs.

## 0. Once per laptop (skip if already done)
1. `powershell -ExecutionPolicy Bypass -File tools\setup.ps1`
2. Double-click `run_selftest.cmd`; `tools\selftest\result.txt` must end with `dry_top_marker` found at `www.wikipedia.org`.
3. Install Playwright for the automation script: `.venv\Scripts\python.exe -m pip install playwright`
   (no `playwright install` needed: the script uses your installed Edge).

## 1. Setup run: install Sider and sign in
    powershell -ExecutionPolicy Bypass -File tools\record.ps1 -Assistant sider -Experiment E0 -Run 1
In the Edge window: install **Sider** from the Edge Add-ons store, sign in with a **throwaway** account (never your
own), pin its icon (puzzle-piece menu > pin), open its chat once and choose the default free model. Close the window.
Write the Sider version and the model in `evidence\sider\lab_notes.md`.

## 2. Probe: check the script can see Sider's chat
    .venv\Scripts\python.exe tools\auto_sider.py probe
Edge opens; open Sider's chat when asked. The script writes `evidence\sider\probe.txt` and a screenshot.
Check `probe.txt`:
- `chat found in:` shows a `chrome-extension://...` address: good.
- `New chat button:` shows a label: good. If it says NOT FOUND, the script will ask you to click New chat by hand
  (press Enter in PowerShell after clicking), which is fine. If you'd rather it be fully automatic, send `probe.txt` to
  the team and we set `$env:SIDER_NEW_CHAT`.

## 3. The runs
Leave the Edge window open (the script reuses it). Then:

    .venv\Scripts\python.exe tools\auto_sider.py E1:1 E3:1 E4:1 E1:2 E3:2 E4:2
    .venv\Scripts\python.exe tools\auto_sider.py E2:1 E2:2

Don't touch the Edge window while it runs. Each run writes `evidence\sider\E<n>_run<r>.flow`, a transcript and
screenshots, and adds a line to `lab_notes.md`.

- **Page questions:** Sider only reads the open page when its **Summarize** button (the page chip above the text
  box) is used; a typed question alone does not include the page. So before each page question the script clicks
  Summarize, then asks the question. (`$env:SIDER_PAGE = "0"` turns this off, to record typed questions only.)
- **New chat:** Sider's New chat button has no label the script can find. If the chat is already empty the script
  just continues; otherwise it asks you to click the purple speech bubble above the text box and press Enter, and
  checks that the chat is really empty.
- **Usage limit:** E2 needs 15 prompts per run (42 prompts in total over all runs). If Sider's free plan runs out,
  the script stops with `STOPPED: Sider's usage limit reached`. Delete that run's `.flow` and transcript and redo it
  the next day with the same run number.
- **A run went wrong** (error in the transcript, wrong page, answer cut off): delete its `.flow` and transcript, note
  it in `lab_notes.md` as "discarded: <why>", rerun with the same number.
- **"Sider's chat closed"** in PowerShell: open the chat again in the same tab; the script continues by itself.

## 4. Analyze
    .venv\Scripts\python.exe analysis\sider_report.py evidence\sider test_pages\markers.csv evidence\sider\sider_report.md
    .venv\Scripts\python.exe analysis\score_e2.py evidence\sider\E2_run1_transcript.md evidence\sider\E2_run2_transcript.md > evidence\sider\e2_scoring_first_pass.md
    powershell -ExecutionPolicy Bypass -File tools\analyze.ps1

`sider_report.md` lists per run: hosts (Sider vs third party), Sider's endpoints, the metadata sent with each prompt,
where each marker went, and the page content as uploaded. Check every E2 "yes" by hand.

## 5. Commit (no recordings!)
Copy into `results\sider\`: the transcripts, `screenshots\`, `lab_notes.md`, `sider_report.md`,
`e2_scoring_first_pass.md`. **Never commit `.flow` files** (they hold the login token); upload `evidence\sider\` to
the shared drive. Read `sider_report.md` for the account email or tokens before committing.
Then write `results\sider\RESULTS.md` in the same format as `results\merlin\RESULTS.md`.
