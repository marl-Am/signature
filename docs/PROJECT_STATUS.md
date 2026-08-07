# Signature — Project Status

_This file replaces the old `HANDOFF_N.MD` habit. It is edited in place, not
appended to — when something here gets done, it's deleted, not moved to a
"done" list. Git history is the permanent record; this file is only ever a
snapshot of "true right now." Paste this whole file at the start of a new
chat._

**Live app:** https://signature-j0bv.onrender.com/
**Repo:** https://github.com/marl-Am/signature.git
**Local path:** `C:\Users\marlo\Documents\Github\signature`

---

## Current State

- Live in production. Core functionality (auth, signature builder, tracking,
  Stripe billing, analytics) works end to end, validated in Gmail.
- Local dev now runs against a Neon Postgres `dev` branch (not SQLite), so
  "works locally" and "works in prod" test the same database engine. See
  `WORKFLOW.md` for the full feature workflow.
- Free tier: 1 signature, 3 fonts (Arial, Calibri, Times New Roman),
  fixed accent color, classic layout only, watermark included.
- Pro tier: unlimited signatures, all 11 fonts, custom accent color, all 9
  layout templates, no watermark, priority support.
- Test suite: 102 tests, all passing. `ruff check .` clean. `ty check .`
  clean.
- CI: GitHub Actions, runs on every push to `main`, verified green via
  `gh run list` (not just a local pass — see `CHANGELOG.md` 2026-08-02 for
  why that distinction matters here).
- Landing page's testimonials section (fake client quotes) has been replaced
  with a live interactive signature demo (Alpine.js, `x-text` bindings only —
  no HTML injection surface) paired with a labeled "sample data" analytics
  preview section.
- Tailwind CSS is now compiled at Docker build time via a dedicated Node
  stage in the `Dockerfile`, not loaded from the CDN's in-browser JIT
  compiler. Node/npm never ship in the final runtime image.
- **Outlook and Gmail delivery are both fully tested end-to-end and
  confirmed working in production**: opens, click tracking, SVG-logo
  rejection, and social icons all render/record correctly on the deployed
  site (social icons fixed most recently — no longer merge into one block
  in Outlook). Apple Mail delivery has not been tested yet.
- `SECRET_KEY` and `BREVO_FROM_EMAIL` production guards deployed and
  confirmed live: email verification, email change, password change, and
  account deletion all tested working on the production site.

---

## Open Issues


- [x] ~~Click counts inflated by automated link-scanners~~ — **Fixed and
      deployed 2026-08-06.** IP-range check against Microsoft's published
      Office 365 ranges now filters Safe Links pre-scan clicks, alongside
      the existing User-Agent-based Proofpoint/Barracuda filtering. Live
      Outlook↔Gmail click test showed 5/5 correct link clicks with no
      inflation. Note: fix only prevents new phantom clicks going forward
      — does not retroactively correct already-inflated historical counts.
- [ ] Apple Mail delivery test still outstanding — Outlook and Gmail are
      now both validated end-to-end (opens, clicks, rendering); Apple
      Mail has not been tested yet.

- [x] ~~Total Opens always 0 for Gmail recipients~~ — **Fixed and deployed
      2026-08-07.** Root cause confirmed via live production logs: a
      genuine Gmail open carries a User-Agent containing
      `GoogleImageProxy`, which was on the proxy-exclusion list and
      silently zeroing out every real open. Removed. Live-tested both
      directions: Outlook→Gmail and Gmail→Outlook each showed 1 open / 5
      clicks correctly. Added `tests/test_tracking.py` (11 tests)
      covering this and the pixel/click routes generally, which had no
      direct test coverage before. Side note (not a bug): Gmail-proxied
      opens will always show "Desktop" as device and a fixed generic
      location, since Gmail's proxy masks the real device/IP — inherent
      to how the proxy works, not fixable from our side.

- [ ] **CTR can exceed 100%** — surfaced during the Gmail-opens test: 1
      open + 5 clicks (one per platform link) produced a Click-Through
      Rate of 500%. Not a tracking bug — `total_clicks` and `total_opens`
      are both accurate — but a metric-design question in
      `analytics_service.py`'s CTR formula (`total_clicks / total_opens ×
      100`), which assumes at most one click per open. Needs a decision
      next session: cap CTR at 100%, redefine it as "clicks per open"
      without a percentage framing, or count unique opens-with-any-click
      instead of raw click volume in the numerator.

- [ ] Proton Mail blocks the tracking pixel outright (its own
      tracker-blocking feature) — this is a deliberate recipient privacy
      choice, not a bug, and not something to build around. Noted here
      only so it isn't mistaken for one later.

- [ ] **Brevo sender deliverability risk** — `BREVO_FROM_EMAIL` is
      confirmed set in both local `.env` and Render, but its value is a
      personal Outlook address (`signatureapp.2026@outlook.com`), not a
      domain Brevo has verified/authenticated (SPF/DKIM). Transactional
      email sent through Brevo "from" an unauthenticated domain risks
      spam-folder routing or spoofing flags, independent of whether the
      API key is valid. Same underlying blocker as the existing "Brevo
      domain authentication decision" below — real fix is the custom
      domain purchase, not a code change.
- [ ] `font_family`'s Pro-only set intentionally isn't validated beyond the
      allow-list check — no further action needed, just noting the design
      is deliberate
- [ ] Decide whether to keep `app/static/css/output.css` committed to git or
      remove it (add to `.gitignore`) now that Docker rebuilds it fresh on
      every image — either is fine, just an open decision
- [ ] **Deliberately deferred, not planned:** `app/models/user.py`'s
      `record_failed_login()`/`record_successful_login()` commit directly
      to the database from model methods — consistent with every other
      method in the file, so left alone rather than fixed in isolation
      (see `CHANGELOG.md` 2026-08-01 for full reasoning). Also low-priority
      stylistic-only items from the audit: `tracking.py`'s hardcoded
      platform-mapping dict, and `app/__init__.py`'s monolithic
      `create_app()`. None of these are blocking anything.

## Blocked / Deferred (no action needed, just tracked)

- Custom domain + Zoho Mail — blocked on ~$10-12/year budget
- Render's paid always-on tier — blocked on ~$7/month budget
- Moving Stripe out of test mode — deferred until there's a real onboarding
  plan
- Docker Scout's two remaining failed policies (copyleft license scan,
  supply chain attestations) — low priority
- Brevo domain authentication decision — tied to the domain purchase above;
  also the real fix for the Brevo sender deliverability risk noted above
- Auto-regenerating `html_content` on Stripe webhook tier change — decided
  against, watermark/font/color only update on next manual save

---

## Recently Completed (this section gets replaced, not appended, next session)

**Session: Fixed Gmail opens showing as 0 (2026-08-07)**

- Root-caused via live Render log capture (added temporary diagnostic
  logging to `pixel()`): a genuine Gmail open carries a User-Agent ending
  in "(via ggpht.com GoogleImageProxy)" — that exact string was on
  `_PROXY_SIGNATURES`, silently excluding every real Gmail open.
- Confirmed via a controlled unopened-email test that Gmail isn't
  currently prefetching this app's pixel in the background, so removing
  the exclusion carries no known regression risk.
- Removed `"GoogleImageProxy"` from `_PROXY_SIGNATURES` in `tracking.py`.
- Added `tests/test_tracking.py` (11 new tests, 91 → 102 total) — the
  pixel/click routes had zero direct test coverage before, including the
  2026-08-06 Office 365 Safe Links fix.
- Live-tested both directions: Outlook→Gmail and Gmail→Outlook each
  showed 1 open / 5 clicks correctly, no inflation.
- Surfaced a new, unrelated metric-design issue: CTR can exceed 100% when
  a recipient clicks multiple links per open. Added as a new Open Issue,
  to address next session.

Older completed sessions (cryptography CVE fix, Office 365 Safe Links
click-inflation fix) have moved to `CHANGELOG.md`.

---

## Next Up

- [ ] Decide on the CTR formula fix (cap at 100%, reframe as "clicks per
      open", or count unique opens-with-a-click) and implement it.
- [ ] Pay for a real custom domain and set up Brevo domain authentication.
- [ ] Run an end-to-end Apple Mail delivery test (Outlook and Gmail are
      now both confirmed working).
---

## How This Project Talks to Claude Now

- This file (`PROJECT_STATUS.md`) is the only thing you need to paste at
  the start of a new chat. It should stay under ~150 lines — if it's
  growing past that, something belongs in `CHANGELOG.md` instead.
- `CHANGELOG.md` (separate file, append-only, one line per session) is the
  permanent history, for anything you want to look back on later.
- When code accuracy matters, upload the actual file rather than describing
  it — several bugs this session were only caught by reading the real code,
  not a description of it.