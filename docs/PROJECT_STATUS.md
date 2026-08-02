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
  clean. Confirmed locally after every audit fix this session (`user.py`,
  `tracking.py`, `signatures.py`).
- CI: GitHub Actions, runs on every push to `main`. **Actually verified
  green via `gh run list` as of 2026-08-02** — a prior session's claim
  that CI was "confirmed passing" was wrong; CI had silently been failing
  on every push since the `SECRET_KEY` guard was merged (see
  `CHANGELOG.md` 2026-08-02 for the root cause and fix). Lesson: check
  `gh run list` after every push going forward, don't just trust a local
  green run.
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
- **The full pass-1 code audit (`docs/AUDIT_FINDINGS.md`) is now fully
  triaged and closed out**, and every fix from this session is confirmed
  live in CI (not just locally) — see Recently Completed and
  `CHANGELOG.md` for the complete history.
- `SECRET_KEY` and `BREVO_FROM_EMAIL` production guards deployed and
  confirmed live: email verification, email change, password change, and
  account deletion all tested working on the production site.

---

## Open Issues


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

**Session: full audit triage completed (2026-08-01)**

- Visually confirmed the Solid and Split layouts on the live production
  URL (pushed 2026-07-26, CI/deploy green at the time but never actually
  eyeballed until now) — both render correctly with a Pro-tier signature.
- Fixed a real CI-breaking bug found by actually checking `gh run list`
  instead of assuming a local green run meant CI was fine:
  `ProductionConfig` in `app/config.py` raised at import time (not only
  when actually used), which had been silently failing every CI run since
  the previous session's `SECRET_KEY` guard was merged. Fixed via a
  `ProductionConfig.init_app(app)` hook. See `CHANGELOG.md` 2026-08-02 for
  the full root cause.
- Triaged and fixed every remaining `docs/AUDIT_FINDINGS.md` item:
  - `app/models/user.py` — `is_locked()` no longer mutates state as a side
    effect of a read-only check; split into a pure `is_locked()` and a new
    `clear_expired_lockout()`. Fixed a latent bug this uncovered:
    `record_failed_login()` now calls `clear_expired_lockout()` first, so
    a stale attempt count can't instantly re-lock a user after their
    lockout window has already expired.
  - `app/models/user.py` — extracted a shared `_token_is_valid()` helper
    so `verify_email()`/`reset_password()` no longer duplicate the same
    token-match-and-expiry check.
  - `app/routes/tracking.py` and `app/routes/signatures.py` — narrowed
    four `except Exception:` blocks to `except SQLAlchemyError:` across
    `pixel()`, `click()`, `create()`, and `edit()`. The graceful-continue
    behavior (always serve the GIF, always redirect, flash a friendly
    error) was correct by design and left untouched; the fix only stops
    unrelated bugs from being silently swallowed alongside real database
    failures. Also fixed a related latent bug: `edit()`'s internal second
    call to `get_signature_by_id()` inside `update_signature()` could
    previously have its 404 masked by the bare `except Exception:` on a
    delete-during-edit race condition.
  - Reviewed `app/routes/signatures.py`'s form-duplication finding and
    found it largely already resolved (`_read_signature_form_fields()`
    already exists as the shared helper); judged the remaining
    create/edit shape not worth extracting further with only two callers.
  - Reviewed and deliberately deferred `app/models/user.py`'s
    persistence-in-model finding — every other method in the file follows
    the same commit-in-model convention, so fixing only two would make the
    file inconsistent rather than cleaner.
  - `pytest` (91 passed), `ruff check .` (all checks passed), `ty check .`
    (all checks passed) confirmed clean after every fix.
- Older completed sessions (prod hardening guards, Brevo/SendGrid template
  fixes, `ty.toml` exclusion, `signature_service.py` dedup, initial audit
  run) have moved to `CHANGELOG.md` under `2026-08-01`.

---

## Next Up

- [ ] Pay for a real custom domain and set up Brevo domain authentication —
      resolves both the sender-reputation/Outlook-filtering risk and the
      `BREVO_FROM_EMAIL` deliverability concern above in one step.
- [ ] Run an end-to-end Outlook/Apple Mail delivery test against the live app
      to verify copy/paste and render behavior outside Gmail.


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