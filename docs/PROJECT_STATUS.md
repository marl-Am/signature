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
  layout templates (added `solid` and `split` this session), no watermark,
  priority support.
- Test suite: 91 tests, all passing. `ruff check .` clean. `ty check .`
  passes clean — the Flask-SQLAlchemy `db.Model` MRO false positive is
  resolved via the targeted rule exclusion in [ty.toml](../ty.toml); no app
  logic changes were required. Confirmed 2026-08-01: `pytest` (91 passed),
  `ruff check .` (all checks passed), `ty check .` (all checks passed) —
  re-confirmed again after the `BREVO_FROM_EMAIL` guard, same clean result.
- CI: GitHub Actions, runs on every push to `main`, confirmed passing via
  `gh run list`.
- Landing page's testimonials section (fake client quotes) has been replaced
  with a live interactive signature demo (Alpine.js, `x-text` bindings only —
  no HTML injection surface) paired with a labeled "sample data" analytics
  preview section.
- Tailwind CSS is now compiled at Docker build time via a dedicated Node
  stage in the `Dockerfile`, not loaded from the CDN's in-browser JIT
  compiler. Node/npm never ship in the final runtime image.
- Outlook/Apple Mail install instructions on the preview page were checked
  against current Microsoft/Apple docs and updated where Microsoft's own UI
  rollout has created two possible menu paths. Actual end-to-end send/receive
  testing in those clients is still outstanding (see Open Issues).
- A pass-1 code audit (checklist: `docs/signs-of-llm-generated-code.md`) was
  run across the whole tracked codebase; findings are in
  `docs/AUDIT_FINDINGS.md`. Four items from it have been fixed and verified
  (see Recently Completed), one was checked and confirmed a false positive
  (terms.html/base.html contact copy — see below), and the rest still need a
  confidence/triage pass before any further fixes (see Open Issues).
- Checked `app/templates/terms.html` and `app/templates/base.html` against
  the `privacy.html` fix the audit flagged as inconsistent: the actual fix
  only changed the third-party-provider narrative (SendGrid → Brevo), which
  never existed in the other two files, and the contact address
  (`signatureapp.2026@outlook.com`) was identical across all three the whole
  time and was never part of the fix. No change needed; audit finding was a
  false positive.
- `SECRET_KEY` and `BREVO_FROM_EMAIL` production guards deployed and
  confirmed live (2026-08-01): email verification, email change, password
  change, and account deletion all tested working on the production site,
  and every form was checked. No regressions from either guard.

---

## Open Issues

- [ ] **Solid/Split live visual verification** — pushed, CI green, deploy
      green (2026-07-26), but not yet visually confirmed on the live URL.
      Same verification gap as prior sessions closed by actually visiting
      the live site rather than trusting a green build: create a Pro-tier
      signature with each of the two new layouts and check they render as
      intended, especially since they're the first layouts to use a
      colored background as the entire card rather than just an accent
      line or header band.
- [ ] **Outlook/Apple Mail delivery test** — the create → copy → paste →
      send → receive flow has only been validated in Gmail. UI install
      instructions exist for all three clients, but Outlook/Apple Mail
      haven't been tested end to end.
- [ ] **Brevo sender deliverability risk** — `BREVO_FROM_EMAIL` is
      confirmed set in both local `.env` and Render, but its value is a
      personal Outlook address (`signatureapp.2026@outlook.com`), not a
      domain Brevo has verified/authenticated (SPF/DKIM). Transactional
      email sent through Brevo "from" an unauthenticated domain risks
      spam-folder routing or spoofing flags, independent of whether the
      API key is valid. Same underlying blocker as the existing "Brevo
      domain authentication decision" below — real fix is the custom
      domain purchase, not a code change.
- [ ] Consider a regression test or manual QA checklist item for the
      clipboard-copy background bug (fixed in an earlier session)
- [ ] Existing signatures created before a certain point have old relative
      tracking URLs (data issue, not a code bug)
- [ ] `font_family`'s Pro-only set intentionally isn't validated beyond the
      allow-list check — no further action needed, just noting the design
      is deliberate (see Recently Completed below)
- [ ] Decide whether to keep `app/static/css/output.css` committed to git or
      remove it (add to `.gitignore`) now that Docker rebuilds it fresh on
      every image — either is fine, just an open decision
- [ ] Full pass-1 audit findings not yet triaged beyond this session's four
      fixes — remaining items (model-layer duplication in
      `verify_email`/`reset_password` token-validity checks in `user.py`;
      `is_locked()` performing a write inside a read-style guard;
      `signature_service.py` create/update duplication;
      `signatures.py` form-handling duplication between create/edit;
      broad exception handling in `tracking.py`'s pixel/click endpoints)
      are documented in `docs/AUDIT_FINDINGS.md` and still need a
      confidence pass before anything is fixed.

**Cheap Pro-tier design features not yet built** (same gating pattern as
accent color/font family/layout — form field → route passes through
unconditionally → service layer enforces tier + validates input):

- [ ] Divider/border style options (easiest)
- [ ] Avatar shape variants (easy)
- [ ] Social icon row (needs Simple Icons SVG assets, free/CC0)
- [ ] QR code / vCard button (needs the `qrcode` Python package, free)

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

**Session: prod hardening + audit cleanup (2026-08-01)**

- Verified the `FLASK_ENV` app-level check in [wsgi.py](../wsgi.py) is not
  using any Flask-internal behavior removed in Flask 3.x; it is just a
  custom config switch and did not require a runtime fix.
- Fixed the production-only secret guard in [app/config.py](app/config.py):
  `SECRET_KEY` now fails loudly in production if missing, while
  local/dev/test runs still keep the safe fallback for easier startup.
- Fixed the stale Brevo/SendGrid mismatch and placeholder live-domain
  issues:
  - [app/services/email_service.py](app/services/email_service.py): welcome
    email now uses the real app base URL and the configured sender
    fallback
  - [app/templates/privacy.html](app/templates/privacy.html): updated to
    Brevo and removed stale SendGrid copy
- Added a targeted `ty` exclusion in [ty.toml](../ty.toml) to ignore the
  Flask-SQLAlchemy `unsupported-base` false positive without rewriting the
  ORM models.
- Added the same fail-loudly production guard pattern to
  `BREVO_FROM_EMAIL` in [app/config.py](app/config.py) via a new
  `get_brevo_from_email_for_config()` helper, mirroring
  `get_secret_key_for_config()`. Confirmed Render and local `.env` both
  have the variable set before applying the guard, so this is a hardening
  change, not a live fix.
- Ran a full pass-1 codebase audit (checklist-driven, no edits) across
  `app/models`, `app/services`, `app/routes`, `app/templates`, and
  remaining tracked config/bootstrap files. Findings recorded in
  `docs/AUDIT_FINDINGS.md`.
- Checked the audit's `terms.html`/`base.html` contact-copy finding against
  the actual `privacy.html` diff and confirmed it was a false positive —
  no fix needed (see Current State for detail).
- Validation confirmed 2026-08-01: `pytest` (91 passed), `ruff check .`
  (all checks passed), `ty check .` (all checks passed) — clean after both
  the `SECRET_KEY` and `BREVO_FROM_EMAIL` guards.
- Deployed to production and confirmed live: email verification, email
  change, password change, and account deletion all tested working on the
  real deployed URL, along with every other form in the app. No regressions
  from either guard.

---

## Next Up

- [ ] Pay for a real custom domain and set up Brevo domain authentication —
      resolves both the sender-reputation/Outlook-filtering risk and the
      `BREVO_FROM_EMAIL` deliverability concern above in one step.
- [ ] Run an end-to-end Outlook/Apple Mail delivery test against the live app
      to verify copy/paste and render behavior outside Gmail.
- [ ] Do a live visual QA pass on the Solid/Split layouts on the production
      URL.
- [ ] Triage the remaining `docs/AUDIT_FINDINGS.md` items by confidence
      level before fixing anything further.

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