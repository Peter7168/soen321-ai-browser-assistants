# Contribution log

## Peter
- Set up the recording toolkit: Mitmproxy with Microsoft Edge in a separate test profile, without installing a root certificate (`tools/setup.ps1`, `tools/record.ps1`)
- Built the automatic self-test that checks recording and HTTPS decryption end to end (`tools/selftest.ps1`)
- Wrote the analysis scripts that search recordings for our fake data and list who received it (`analysis/`)
- Made the test pages, the fake persona and the runbook page with every prompt for E1 to E4 (`test_pages/`)
- Wrote the setup guide for the team (`SETUP_GUIDE.md`)
- Automated the Copilot in Edge experiments over Edge's DevTools protocol (`tools/auto_copilot.py`)
- Ran E1 to E4 on Copilot in Edge, analyzed the recordings and wrote up the results (`results/copilot/`)
- Set up this repository

## Andrii
-

## Maria-Christine
- Ran E1 to E4 on Sider (2 runs each), analyzed the recordings and wrote up the results (`results/sider/`)
- Automated the Sider experiments over Edge's DevTools protocol, with a probe mode to check the setup first (`tools/auto_sider.py`)
- Wrote the Sider analysis script, which searches every request and WebSocket message without needing Sider's message format (`analysis/sider_report.py`)
- Wrote the Sider run guide (`results/sider/HOW_TO_RUN.md`) and extended the E2 scoring to Sider and Perplexity transcripts

## Parsa
-

## Georges
- Ran E1 to E4 on Merlin (2 runs each), analyzed the recordings and wrote up the results (`results/merlin/`)
- Automated the Merlin experiments over Edge's DevTools protocol (`tools/auto_merlin.py`)
- Wrote the Merlin analysis script (`analysis/merlin_report.py`)

## Mohamed
-
