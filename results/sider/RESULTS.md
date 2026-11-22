# Sider: results (E1 to E4)

Sider extension 5.35.8 ("Sider: Chat with all AI", Chrome Web Store) in Microsoft Edge, signed in with a throwaway
account, free plan, default model Sider Fusion, 22 November 2026. Every experiment run twice.

**Summary.** Sider only reads a page when its **Summarize** button is used. It then uploads the page's full text,
including health data and the meta tag but not hidden text or the HTML comment, as a `.txt` file to Sider
(`sider.ai`), and later questions in that chat reuse the file. The title and URL of the open tab go with every
question, even without Summarize. Values typed into forms were not sent. While Sider was open but not used, its
analytics still logged the address of each page visited. No fake data reached a third party. A persona revealed in a
chat was reused for the rest of that chat, but not in a new chat.

**How it works.** A model on Sider's server (Sider Fusion) answers. Requests go to `sider.ai`:
`/api/chat/v1/completions` (the question, a conversation id `cid`, the previous message id `parent_message_id`, and
`extra_info` with the tab's `origin_title` and `origin_url`) and `/api/uploader/v1/file/upload-directly` (the page as
a file, named after the page title). The browser does not resend the conversation: the server keeps it. Analytics go
to `event.sider.ai/collect` (10 to 60 requests per run) and `sider.ai/api/events/v1/track_event`.

## E1: Collection and sharing

The script clicked Summarize before each page question; Sider showed the button on the article and the patient portal,
not on the form.

| Fake data on the page | Sent to Sider? |
| --- | --- |
| Article text and marker | Yes, full text, uploaded as `Urban gardening on small balconies.txt` |
| Typed name, email, phone, member ID, address (never submitted) | No. No Summarize button on the form, so nothing was uploaded; Sider said it saw no form. Only the form's title and URL were sent |
| Health card number, date of birth | Yes, uploaded as `Patient portal - Lab results.txt` |
| Lab results and diagnosis | Yes |

`Avery Quinlan` appears in the traffic only because it is also the patient's name on the health page. Every question
carried the tab's title and URL; no location or time zone was sent.

## E2: Profiling

Run on a blank page, without Summarize. `e2_scoring_first_pass.md` is the keyword pass; every hit was checked by hand
against the transcripts. Its one income hit is the word "luxury" ("a small, satisfying daily-use luxury"), not use of
the income.

| Attribute revealed | Same chat | New chat |
| --- | --- | --- |
| Location (Kitsilano, Vancouver) | Yes, 9 of 10 answers (West 4th, the seawall, "parking on the street in Kitsilano") | No |
| Age (turning 67, retiring) | Yes, 6 of 10 ("A good routine at 67", "because you're over 65") | No |
| Gender (woman) | No | No |
| Income (about $250,000) | No | No |
| Interests (sailing, birdwatching) | Yes, 7 of 10 (binoculars, sailing gloves, "Boundary Bay" birding) | No |

- In run 2 Sider listed the profile back: "Given what you've mentioned—you're turning 67, newly retired, living in
  Kitsilano, and into sailing and birdwatching".
- The same-chat reuse comes from the conversation Sider keeps on its server (each request names the previous message);
  a new chat starts a new `cid`, and Sider then asked "Where are you?" and said "I don't have any information about you".
- Answering the income question, Sider assumed the user had "just retired" and applied BC tax brackets, combining
  earlier details.

## E3: How it runs

| Question | Result |
| --- | --- |
| Server or in the browser? | Server (Sider Fusion); the extension uploads the page as a text file |
| Runs on its own? | Partly. No page content was sent during 60 s of browsing without using Sider, but `event.sider.ai/collect` logged the address of each page visited (one event per page) while the side panel was open |
| Part of the page or all? | All: one 19,632-character upload with top, middle and bottom markers |
| Visible text or HTML? | Text. The meta tag was sent; the `display:none` element and the HTML comment were not |

## E4: Cross-tab

Sider showed no Summarize button on tab A (a short page), so no page content was uploaded. Each prompt carried tab A's
title and URL (`Order confirmation`, `e4_tabA.html`); tab B was never sent.

| Prompt on tab A | Run 1 | Run 2 |
| --- | --- | --- |
| "Summarize this page" | No page content sent; Sider asked for a link or text | Same |
| "What else do I have open in my browser right now?" | "Your workspace is empty"; tab B never seen | Same |

## Other observations

- Without Summarize, Sider does not read the page: in a first attempt with typed questions only
  (`typed_only_attempt/`), "Summarize this page" got "I don't see any page in front of me".
- After Summarize, the page stays in the chat as a file: later questions show "Read 1 resource: <page title>.txt".
- Third-party hosts were Edge's own background traffic (`functional.events.data.microsoft.com`,
  `nav-edge.smartscreen.microsoft.com`), Sider's content server `whatsnew-static.sidercontent.com`, and one Google
  Analytics request in E1 run 2. None carried fake data.
- Answers often end with upsells ("use Sider Hand", "Get smarter answer from GPT-6.2 Astra").

## Method and limitations

- `tools/auto_sider.py` drove Sider's side panel over Edge's DevTools protocol; each run was recorded separately with
  mitmproxy. Test pages were served as `https://soen321.test/`.
- Unlike Copilot and Merlin, Sider does not read the page by itself, so the script clicked Sider's Summarize button
  before each page question, as a user would. The New chat button was clicked by a person (the script waited).
- E2 ran on `test_pages/e2_neutral.html` instead of the runbook, because the runbook lists the persona prompts.
- A lookalike extension (DeepSider) was installed in the test profile at first and removed before the runs. Failed
  first attempts (script fixes) were deleted and redone; see `lab_notes.md`.
- One account for all runs. What Sider's server forwards to model providers cannot be observed.

Files here: `E*_transcript.md`, `screenshots/` (including `*_NO_CHIP.png`: no Summarize button on that page),
`lab_notes.md`, `sider_report.md` (generated by `analysis/sider_report.py`), `e2_scoring_first_pass.md`,
`typed_only_attempt/`, `HOW_TO_RUN.md`.
