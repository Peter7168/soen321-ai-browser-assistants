# SOEN 321 - Recording setup guide (Windows + Microsoft Edge)

Everything runs from this folder. You need Windows, Microsoft Edge and Python 3 (python.org, tick "Add to PATH").
Nothing is installed in your Windows certificate store and your normal Edge is not touched: the recordings use
separate Edge profiles stored in `profiles\`.

## 1. One-time setup (about 2 minutes)
Open PowerShell in this folder (Shift + right-click the folder > "Open PowerShell window here") and run:

    powershell -ExecutionPolicy Bypass -File tools\setup.ps1

It creates a private Python environment (`.venv`), installs mitmproxy into it, and saves mitmproxy's key
fingerprint to `tools\spki.txt`. Edge is told to trust only that key, only in our test windows.

## 2. Quick automatic check
Double-click `run_selftest.cmd`. It runs a hidden Edge window through the recorder for about 20 seconds and writes
the outcome to `tools\selftest\result.txt`. It passed if the last analysis line shows `dry_top_marker` found at
`www.wikipedia.org`.

## 2b. Manual dry run (optional, to see the real window)

    powershell -ExecutionPolicy Bypass -File tools\record.ps1 -Assistant dryrun -Experiment E0 -Run 1

An Edge window opens on our test pages. Click "Dry run", type the name and email shown on the page, click the
button, wait for "Sent", then close that Edge window. Then:

    powershell -ExecutionPolicy Bypass -File tools\analyze.ps1

Expected: under `== dryrun` you see the markers and the form name/email found at `127.0.0.1` (local test server)
and `ZQX-DRY-TOP-4417` found at `www.wikipedia.org`. The wikipedia.org hit proves HTTPS decryption works.

## 3. Baseline (once per laptop)
Records what Edge sends with no assistant, so we can ignore Edge's own background traffic:

    powershell -ExecutionPolicy Bypass -File tools\record.ps1 -Assistant baseline -Experiment E0 -Run 1

Browse the test pages for a minute, close the window.

## 4. Real experiments
First time only, open your assistant's profile and install + log in to the extension:

    powershell -ExecutionPolicy Bypass -File tools\record.ps1 -Assistant sider -Experiment E0 -Run 1

(Install from the Edge Add-ons store, log in with the throwaway account, close the window. This E0 recording is
just the setup, keep it anyway.) Then for each experiment and run:

    powershell -ExecutionPolicy Bypass -File tools\record.ps1 -Assistant sider -Experiment E1 -Run 1

`-Assistant` is one of `copilot`, `sider`, `merlin`, `perplexity`. Do exactly one experiment per window, then close
it. The recording lands in `evidence\<assistant>\E1_run1.flow` and a line is added to
`evidence\<assistant>\lab_notes.md`: add the assistant version and anything unexpected there.
Save screenshots of every answer in `evidence\<assistant>\screenshots\` named like `E2_run1_sametab_q1.png`.

To look at a recording by hand: `.venv\Scripts\mitmweb.exe -r evidence\sider\E1_run1.flow`

## 5. Hand in
Upload your whole `evidence\<assistant>\` folder to the shared drive. Do not upload `profiles\` or `.venv\`.

## Troubleshooting
- "port 8899 already in use": a previous recording is still running. Close leftover mitmdump windows and retry.
- Edge shows a certificate error on a site: run `tools\setup.ps1` again, then retry. Tell Peter which site.
- Edge says "You are using an unsupported command-line flag": expected, ignore it.
- When done with the whole project, delete `%USERPROFILE%\.mitmproxy` to remove the key.
