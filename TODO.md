# Project status and remaining tasks

Read this first if you are picking up the project (person or AI agent). Updated 2026-11-19.

## Goal
Measure 4 AI browser assistants (Copilot in Edge, Sider, Merlin, Perplexity) with 4 experiments each, following
Vekaria et al., USENIX Security 2025. Each assistant: E1 to E4, 2 runs each = 8 recordings.

| Experiment | Question |
| --- | --- |
| E1 | What page data, typed form values and identifiers are sent, and to whom? |
| E2 | Does it profile the user (location, age, gender, income, interests) and reuse it in the same chat / a new chat? |
| E3 | Server or browser? Does it run on its own? Part or all of the page? Text or HTML? |
| E4 | Does data from one tab leak into a request about another tab? |

## Done
- [x] Recording toolkit for Windows + Edge + mitmproxy, verified end to end (`tools/`, `run_selftest.cmd`)
- [x] Test pages, fake persona, markers, runbook with every prompt (`test_pages/`)
- [x] Analysis scripts (`analysis/`)
- [x] Team setup guide (`SETUP_GUIDE.md`)
- [x] **Copilot in Edge: all four experiments done and written up** (`results/copilot/RESULTS.md`)
- [x] **Merlin: all four experiments done (2 runs each) and written up** (`results/merlin/RESULTS.md`)
- [x] **Sider: all four experiments done (2 runs each) and written up** (`results/sider/RESULTS.md`)

## Remaining tasks

### Experiments
- [ ] **Perplexity**: E1 to E4, 2 runs each
- [ ] Copilot, optional: finish E2 run 4's new-chat questions (stopped at the daily limit)
- [ ] Copilot, optional: check by hand whether Copilot asks permission before reading other tabs

### Analysis and writing
- [ ] Run the analysis on each assistant's recordings and write `results/<assistant>/RESULTS.md` in the same format as Copilot's
- [ ] Score E2 per assistant (`analysis/score_e2.py` first pass, then check every hit by hand)
- [ ] Cross-assistant comparison table: 4 assistants x 4 experiments
- [ ] Report: introduction, background, related work; methodology; results per experiment; discussion; limitations; conclusion
- [ ] Slides
- [ ] Final proofread and references
- [ ] Each person fills in their section of `CONTRIBUTIONS.md`

## How to do an assistant (what you can reuse)
1. Follow `SETUP_GUIDE.md`: run `tools/setup.ps1` once, then `run_selftest.cmd` to confirm recording works.
2. First run: `tools/record.ps1 -Assistant <name> -Experiment E0 -Run 1`. Install the extension from the Edge Add-ons store and sign in with a throwaway account.
3. For each experiment and run: `tools/record.ps1 -Assistant <name> -Experiment E1 -Run 1` and so on. The Edge window opens on the runbook page (`test_pages/index.html`) with the steps and copy buttons for every prompt. Close the window to save.
4. Analyze: `tools/analyze.ps1` (generic, needs mitmproxy) writes `analysis/output/summary.txt`. `analysis/copilot_report.py` works without mitmproxy and decodes Copilot's chat format; its marker search, host list and tnetstring reader (`analysis/tnetstring_reader.py`) work for any assistant, but the chat-message parsing must be adapted to each extension's own format.
5. Put transcripts, screenshots, `lab_notes.md` and `RESULTS.md` in `results/<name>/`. **Never commit `.flow` files** (they contain login tokens); keep them on the shared drive.

`tools/auto_merlin.py` automates Merlin the same way; `analysis/merlin_report.py` decodes its chat format.
`tools/auto_sider.py` automates Sider; it finds the chat box and buttons by role, so `tools/auto_sider.py probe` shows
what it can see before the real runs. `analysis/sider_report.py` does not need Sider's format: it searches every
request and WebSocket message, so it is a good starting point for Perplexity too.

`tools/auto_copilot.py` automates Copilot only (its sidebar is a page reachable over Edge's DevTools protocol). An
extension's side panel or popup may also be reachable that way (launch Edge with `--remote-debugging-port`, list
targets at `http://127.0.0.1:9333/json/list`); the selectors and the "answer finished" check would need rewriting.

## Lessons learned (save yourself time)
- Recording does not touch the Windows certificate store: Edge trusts mitmproxy's key only in the test window (`--ignore-certificate-errors-spki-list`).
- Chromium skips the proxy for localhost unless `--proxy-bypass-list=<-loopback>` is set (already in the scripts).
- Some home networks cannot resolve certain domains (example.com failed on one laptop). `tools/selftest/result.txt` shows the mitmproxy log.
- Kill the leftover mitmdump/http.server processes after a crash, or ports 8899/8765 stay busy and files stay locked.
- On Windows, set `PYTHONIOENCODING=utf-8` (or reconfigure stdout); assistant answers contain characters cp1252 cannot print.
- Copilot: the sidebar cannot be opened by script and does not reopen after Edge restarts, so a person clicks it once per session; it sometimes answers with a multiple-choice question that hides the input (click Skip); the free account has a daily usage limit, so E2 (15 prompts) may need two sittings.
- Assistant chat traffic is often a WebSocket, not normal requests: check client-to-server WebSocket messages, not only request bodies.
- Number markers (like an age "67") match random traffic; use unique codes like `ZQX-E1-FRM-6612` as markers.
- Merlin: only reads `https://` pages (`auto_merlin.py` serves the test pages as `https://soen321.test/`).
- Sider: only reads the page when its Summarize button is clicked (the script does this), and only shows that button
  on article-like pages. Its New chat button has no label, so a person clicks it when the script asks. Install the real
  "Sider: Chat with all AI" (sider.ai); lookalikes such as DeepSider exist.
- An assistant that reads the open tab will read the runbook, which lists the persona prompts. Run E2 on
  `test_pages/e2_neutral.html`.

## Conventions
- Recordings: `evidence/<assistant>/E<n>_run<r>.flow` (created by `record.ps1`, never committed)
- Screenshots: `E2_run1_newtab_q3.png` style names
- Every run gets a line in `lab_notes.md`: assistant version, date, anything unexpected
- All personal data in tests is fake; use throwaway accounts only
