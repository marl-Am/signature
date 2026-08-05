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


- [ ] **Click counts inflated by automated link-scanners** — confirmed via
      raw `signature_clicks` rows that some providers' security scanners
      visit every link in a real browser before/on open, adding phantom
      clicks with no reliable self-identifying signal (unlike the
      Gmail-proxy case, already handled). Known industry-wide limitation,
      still not fixed. A burst-detection heuristic was considered and
      deliberately deferred, since a fast genuine human clicking several
      links back-to-back would look identical, and getting it wrong risks
      undercounting real engagement. **An IP-range-matching approach
      (checking click source IP against Microsoft's published Office 365
      ranges, to catch Outlook Safe Links' pre-delivery scan bot) was
      designed and code was drafted in a prior session, but was NOT
      applied to this repo** — it required a `ProxyFix` change in
      `app/__init__.py` that turned out to be wrong for this app's actual
      deployment (assumed a Cloudflare hop that doesn't exist without a
      custom domain — see `CHANGELOG.md` 2026-08-02 cont. 7 for the full
      writeup) and was judged too complex to be worth the risk right now.
      Revisit later if desired; the changelog entry has the corrected
      reasoning so it isn't re-derived from scratch.
- [ ] Apple Mail delivery test still outstanding — Outlook and Gmail are
      now both validated end-to-end (opens, clicks, rendering); Apple
      Mail has not been tested yet.

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

**Session: Celery + Redis explored for resume purposes, then fully reverted (2026-08-05)**

- Explored adding Celery + Redis purely for resume/interview signal (not
  fixing anything broken). Built a complete, locally-verified integration
  (Redis via Render's free Key Value tier, `app/celery_app.py`,
  `app/tasks.py`, all 5 email call sites switched to `.delay(...)`, a
  test fixture keeping `pytest` off real Redis) — 91 tests passed.
- Hit a real cost wall trying to run it live: Render's free compute tier
  covers web services, Postgres, and Key Value, but **not** background
  workers ($7+/month on any plan) — verified directly against Render's
  own pricing and docs after an earlier wrong assumption in this same
  session.
- Tested a free workaround (running the worker as a thread inside the
  existing free web service) and found it **unsafe**: it silently kills
  the whole process, since Celery's worker assumes it owns the entire
  process including OS signal handling. See `CHANGELOG.md` 2026-08-05 for
  the full technical writeup.
- Decided to fully revert rather than ship a half-integration: deleted
  `app/celery_app.py`/`app/tasks.py`, restored the original direct
  email-sending code everywhere, removed the test fixture and the
  `celery`/`redis` dependencies. Tests clean, deployed, confirmed working
  — app is functionally identical to before this session.
- A free, unused `signature-redis` Key Value instance may still exist on
  the Render dashboard — costs nothing either way, safe to delete or keep.
- Older completed sessions (click-count scanner-filtering exploration,
  social icon table fix) have moved to `CHANGELOG.md`.
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