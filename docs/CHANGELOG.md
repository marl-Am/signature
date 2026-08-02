# Signature — Changelog

Permanent, append-only history. One entry per session, dated, no explanation
beyond a line or two. This file is allowed to grow forever, unlike
`PROJECT_STATUS.md`, which only ever reflects "true right now."

*Note: this changelog starts from what could be confidently verified in
`HANDOFF_22.MD` and this conversation. Sessions not referenced by either are
not included — there were reportedly ~18 more before this list starts.
If you want them added, paste the old handoff files in and they can be
backfilled accurately instead of guessed at.*

---

## 2026-08-01: Prod hardening + first full codebase audit
Fixed `verify_email()` bypassing the service layer (route called the model
directly and discarded the success/failure result — expired tokens still
reported success), and `delete_account()` logging `user.id` after the row
was already deleted and committed. Added fail-loudly production guards for
`SECRET_KEY` and `BREVO_FROM_EMAIL` in `app/config.py` (dev/test keep safe
fallbacks); confirmed both env vars were already set in Render before
adding the guards, so neither was a live-exposure fix, both are hardening.
Fixed the stale SendGrid reference in `privacy.html` (actual provider is
Brevo) and the hardcoded placeholder URL in the welcome email. Added a
targeted `ty.toml` exclusion for the long-standing Flask-SQLAlchemy
`db.Model` MRO false positive — resolved without touching the ORM models.
Ran the project's first full pass-1 codebase audit against
`docs/signs-of-llm-generated-code.md`, covering every git-tracked file;
findings logged in `docs/AUDIT_FINDINGS.md` for future triage. Checked one
audit finding (`terms.html`/`base.html` contact copy vs. `privacy.html`)
and confirmed it was a false positive — no fix needed. Flagged a new,
separate concern: `BREVO_FROM_EMAIL` is a personal Outlook address, not a
Brevo-authenticated domain, which is a deliverability risk tied to the
existing custom-domain decision, not a code bug. Test suite: 91 tests,
all passing throughout. `ruff check .` clean. `ty check .` clean. Deployed
and confirmed live: email verification, email change, password change,
and account deletion all tested working on the production site, along
with every other form in the app.

## 2026-07-31: Added CSRF protection app-wide via Flask-WTF 
— wired CSRFProtect into the app factory, added the hidden token to all 11 POST
forms, exempted the Stripe webhook route (protected by Stripe's own
signature verification instead). Verified locally via Stripe CLI and
confirmed working in production with a real upgrade.


## 2026-07-30: Auth template audit 
— fixed title collision (forgot/reset password), missing minlength/autocomplete on register.html, restyled
reset_password.html to match shared design, extracted repeated input
markup into app/templates/auth/_form_macros.html. Flagged CSRF as
unimplemented — tracked as Open Issue.

## 2026-07-26 — Solid and Split layout templates
Added two new Pro-tier signature layouts: `solid` (entire signature on a
solid accent-colored card, white text throughout, white social badges with
accent-colored text for contrast) and `split` (colored left rail with
avatar/initials, white right column reusing the existing on-white
name/title/contact/social blocks unchanged). Added both to
`SignatureService.PRO_LAYOUTS` and two new `_generate_html_content` branches
following the existing per-layout pattern. Mirrored both into the Alpine.js
live-preview logic and added matching layout-picker tiles in `create.html`
and `edit.html`. While in `edit.html`, found and fixed two small
pre-existing bugs in its `avatar` layout preview (missing department line;
logo `<img>` missing `width`/`height`/`object-fit`, unlike the same branch
in `create.html`). Added 8 new tests to `test_signatures.py` covering
free-tier fallback, Pro-tier access, edit persistence, and the downgrade
case for both new layouts (didn't repeat the unknown-value and
free-tier-classic-still-works cases, since `_sanitize_layout` handles those
generically and they're already covered by the existing `avatar` tests).
Test suite: 78 → 86, all passing. `ruff check .` clean. `ty check .` surfaced
4 warnings (Flask-SQLAlchemy `db.Model` base-class MRO resolution in
`analytics.py`, `signature.py`, `user.py` — none of which were touched
today). Confirmed via `pip show ty` that the installed version (`0.0.61`)
matches the pin, ruling out version drift as the cause; most likely a
pre-existing false-positive inherent to Flask-SQLAlchemy's dynamically
generated declarative base, not a real type error. Not yet deployed —
pending a decision on whether to silence the `ty` warnings or ship as-is.

## 2026-07-25 — Pro-tier layout template gating
Discovered that all seven signature layouts (`classic`, `modern`, `minimal`,
`ruled`, `avatar`, `compact`, `banner`) were already fully built and
rendering correctly, but had no tier enforcement at all — unlike
`accent_color` and `font_family`, any free-tier account could select any of
the six premium layouts directly in the create/edit UI (no crafted request
required) and it would save and render. Added `SignatureService.FREE_LAYOUTS`
/ `PRO_LAYOUTS` and a `_sanitize_layout()` method mirroring the existing
`_sanitize_font_family()` pattern exactly; free tier is now locked to
`classic`, Pro unlocks all seven. Locked the six Pro-only tiles in both
`create.html` and `edit.html` with a disabled state, a "Pro" badge, and an
"Upgrade to unlock" note, matching the existing accent-color lock UI. Added
six new tests to `test_signatures.py` covering free-tier submission
fallback, Pro-tier access, unknown-value fallback, edit persistence, and the
downgrade case. Test suite: 72 → 78, all passing. Deployed and confirmed
live.

## 2026-07-25 — Live URL Tailwind verification
Confirmed on the actual deployed URL (not just local `docker build`/`docker
run`) that the Tailwind CSS build migration renders correctly — visited the
live site and completed a real signature creation, styling intact.

## 2026-07-25 — .gitignore/.dockerignore audit
Audited both files; `node_modules/` and the stray shell-redirect filenames
(`tatus`, `status`) were already correctly excluded, no action needed there.
Found and fixed a real bug: `.gitignore`'s `docs/` and bare `docs` patterns
excluded the directory itself, which silently disables any later `!`
negation pattern for files inside it (Git never traverses an excluded
directory, so re-inclusion rules for files inside it never evaluate).
`docs/architecture.md` happened to already be tracked so this hadn't caused
a problem yet, but a future untrack/re-add or fresh clone would have
silently failed to re-include it. Fixed by changing the pattern to `docs/*`
paired with `!docs/architecture.md`, and removing the bare `docs` line.
Also discovered `docs/PROJECT_STATUS.md` itself had never been committed to
git at all; tracked it for the first time under the same negation pattern.

## 2026-07-25 — Landing page overhaul + Tailwind build migration + repo cleanup
Replaced the fake testimonials section with a live interactive signature demo
(Alpine.js, `x-text`-only bindings) and a labeled sample analytics preview.
Migrated Tailwind CSS off the CDN's in-browser JIT compiler to a proper
compiled build (`tailwind.config.js`, `input.css`, `package.json`). Added a
third Docker build stage (`node:20-slim`) that compiles the CSS at image-build
time and copies only `output.css` into the runtime stage — Node never ships
in the final image. Verified via local `docker build` + `docker run`. Checked
Outlook/Apple Mail install instructions against current docs and updated the
New Outlook/web steps for Microsoft's in-progress UI rollout. Confirmed the
stale `test-workflow` branch was already gone, deleted unused
`requirements-dev.txt`, discovered `ty` had only been installed via that file
and added `ty==0.0.61` to `requirements.txt`, and fixed three stale lines in
`README.md`.

## 2026-07-25 — Local dev workflow + Pro-tier design features
Fixed local/production database mismatch (Neon `dev` branch replaces SQLite
fallback). Documented feature workflow in `WORKFLOW.md`. Built Pro-tier
accent color and Pro-tier font selection (3 fonts free, 11 Pro), both gated
at the service layer with allow-list validation. Found and fixed a stored-XSS
gap in `accent_color`/`font_family` (unescaped in `style=""` attributes,
same bug class as the session 19 fix). Fixed a missing `</div>` that broke
the Live Preview layout. Test suite: 62 → 72, all passing. Deployed and
confirmed live. Retired the `HANDOFF_N.MD` habit in favor of
`PROJECT_STATUS.md` (edited in place) + this changelog (append-only).

## Session 22 (date unconfirmed — see original handoff if needed)
Rewrote `README.md` to reflect live production status. Created
`docs/architecture.md` from scratch (Mermaid diagrams, OWASP table, clipboard
bug case study). Added 16 XSS regression tests for the session 19 stored XSS
fix. Added the free-tier signature watermark feature (previously marketing
copy only) plus 5 regression tests. Corrected inaccurate pricing/homepage
copy (Pro customization, tiered analytics claims that didn't match the code).

## Session 21 (date unconfirmed)
Diagnosed and fixed the clipboard-copy background bug: signatures pasted
outside the app inherited the site's own navy page background due to how
`document.execCommand('copy')` serializes rich-text copies of off-screen
elements. Fixed by explicitly setting the temporary copy element's
background to white.

## Session 19 (date unconfirmed)
Identified and remediated a stored XSS vulnerability in the signature HTML
generation pipeline — unescaped user input in the server-side HTML builder,
fixed with proper escaping and URL scheme validation.

## Session 11 (date unconfirmed)
Some point around here, tracking URL generation changed. Signatures created
before this session still carry old relative tracking URLs (known, low
priority, data-only issue, not a code bug).