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
- Test suite: 91 tests, all passing. `ruff check .` clean. `ty check .`
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

- [ ] **Total Opens always 0 for Gmail recipients** — confirmed via
      controlled test (2026-08-06): Outlook→Gmail showed 0 opens even
      after "Show images" was clicked; Gmail→Outlook correctly
      incremented opens by 1. Root cause: Gmail proxies every image load
      (automatic prefetch AND genuine recipient opens) through Google's
      own image-caching proxy, User-Agent containing `GoogleImageProxy`.
      That string is already in `_PROXY_SIGNATURES`, added specifically
      to filter Gmail's automated prefetching — but it can't distinguish
      that from a real "Show images" click, since both produce an
      identical request. Not yet investigated for a fix; removing
      `GoogleImageProxy` outright would undo the original prefetch-
      filtering it was added for.

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

**Session: Office 365 Safe Links click-inflation fix (2026-08-06)**

- Implemented and deployed the IP-range-matching fix drafted 2026-08-03
  (previously undeployed due to a `ProxyFix` hop-count mistake, now
  corrected to `x_for=1, x_proto=1` for this app's actual single-hop
  Render deployment).
- Added `app/services/ip_range_service.py`, wired into `tracking.py` via
  a new `_is_scanner_request()` helper alongside the existing
  `_PROXY_SIGNATURES` UA check.
- 91 tests passed, `ruff`/`ty` clean, manually verified `is_office365_ip()`
  against real IPs before deploy.
- Live-tested Outlook↔Gmail click tracking: 5/5 correct, no inflation.
- Surfaced a new, separate bug during testing: Gmail recipients always
  show 0 opens, root-caused to `GoogleImageProxy` filtering out real
  opens along with automated prefetch. Added as a new Open Issue —
  not yet investigated.

Older completed sessions (cryptography CVE fix, Celery/Redis exploration
and revert) have moved to `CHANGELOG.md`.

---

## Next Up

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