# AI browser assistants: privacy and security measurement

SOEN 321 (Concordia University) team project. We measure what AI assistants built into the browser collect and share,
following the method of Vekaria et al., *"Big Help or Big Brother? Auditing Tracking, Profiling, and Personalization
in Generative AI Assistants"* (USENIX Security 2025).

Assistants studied: **Copilot in Microsoft Edge**, **Sider**, **Merlin** and **Perplexity**.

## Experiments

| ID | Question | What we do |
| --- | --- | --- |
| E1 | What is collected and who receives it? | Ask the assistant about an article, a form with typed (never submitted) fake values, and a fake patient portal |
| E2 | Does it profile the user? | Reveal a fake persona (location, age, gender, income, interests), then ask neutral questions in the same chat and in a new chat |
| E3 | How does it run? | Browse without using it, then ask about a long page with markers in visible text, an HTML comment, a meta tag and a hidden element |
| E4 | Does data cross tabs? | Two tabs with different fake data; ask only about tab A |

All personal data on the test pages is invented.

## Repository layout

```
tools/        recording toolkit (Windows + Edge + mitmproxy)
  setup.ps1       one-time setup: private Python env with mitmproxy
  record.ps1      record one experiment run (opens Edge in a test profile through the proxy)
  analyze.ps1     search all recordings for our fake data and markers
  selftest.ps1    automatic end-to-end check (run_selftest.cmd)
  auto_copilot.py runs E1-E4 on Copilot in Edge automatically over the DevTools protocol
  auto_merlin.py  runs E1-E4 on the Merlin extension automatically (same approach)
test_pages/   runbook page with every prompt, the E1-E4 test pages, markers.csv
analysis/     analysis scripts (generic marker search, Copilot- and Merlin-specific reports, E2 scoring)
results/      per-assistant results: answer transcripts, lab notes, screenshots, reports
```

Setup and usage: see [SETUP_GUIDE.md](SETUP_GUIDE.md). Who did what: [CONTRIBUTIONS.md](CONTRIBUTIONS.md). Status and remaining tasks: [TODO.md](TODO.md).

## Results so far

Copilot in Edge is done; see [results/copilot/RESULTS.md](results/copilot/RESULTS.md).
Merlin is done; see [results/merlin/RESULTS.md](results/merlin/RESULTS.md). Sider and Perplexity are in progress.

## Not in this repository

Raw traffic recordings (`.flow`) are kept off GitHub on purpose: they contain the test accounts' login tokens and
network details. They are available to the course staff on request.
