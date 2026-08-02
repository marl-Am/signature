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

## 2026-08-02 (cont. 3): SVG logo guard with user-facing validation
Found via live Outlook/Gmail/Proton testing that a logo hosted as an SVG
silently failed to render in every tested client (Outlook, Gmail with
images explicitly enabled) with no error and no broken-image indicator —
SVG is not reliably supported as an inline <img> in HTML email, a
client-compatibility gap rather than a network or hotlinking issue.
Added `_sanitize_image_href()` in `signature_service.py` (rejects .svg by
file extension, checked via the URL's path rather than raw text so a query
string like "?ref=x.svg" on an actual .png is never misflagged) as a
defense-in-depth backstop at HTML-generation time, keeping `logo_url` as
the only field routed through it since website/social links aren't
rendered as images. Added a second, user-facing `validate_logo_url()`
check at the route level in both `create()` and `edit()`, following the
existing `UserService.validate_password()`/`validate_email()`
(is_valid, error_message) pattern, so submitting an SVG logo now shows a
specific flash explaining why instead of silently saving with a blank
logo. Fixed a `ty` type-narrowing error this introduced: checked
`logo_error` directly rather than the paired boolean before calling
`flash()`, since `ty` can't correlate two separately-typed tuple elements
even though the function's contract guarantees they're always in sync.
`pytest` (91 passed), `ruff check .`, `ty check .` all clean.

## 2026-08-02 (cont. 2b): Fix ProductionConfig eagerly raising at import time
(Already recorded above under "2026-08-02: Fix ProductionConfig eagerly
raising at import time" — CI had been silently failing since the previous
session's SECRET_KEY guard was merged; fixed via an init_app(app) hook.)

## 2026-08-02 (cont. 4): Live Outlook/Gmail/Proton delivery test — pixel fix, and full findings triage
Ran the project's first true end-to-end delivery test outside Gmail-only
validation: created a test signature, installed it in New Outlook /
Outlook on the web following the app's own instructions, sent to Proton
Mail and Gmail, and cross-checked opens/clicks against the live Analytics
dashboard and raw Neon rows. Found and fixed a real bug: the tracking
pixel used `style="display:none;"`, which Outlook/Microsoft 365 silently
treats as a known tracking-pixel heuristic and skips fetching entirely —
no broken-image icon, no prompt, just never requested. Removed
`display:none` from the pixel `<img>` in `signature_service.py` (a 1×1
image needs no extra hiding); confirmed fixed by re-saving the test
signature and re-sending — Outlook opens now record correctly. Triaged
three further observations from the same test and confirmed none of them
are code bugs:
  - Gmail holding "Total Opens" at 1 despite multiple opens — expected;
    Gmail's image-caching proxy is already excluded from open counts via
    the existing `_PROXY_SIGNATURES` list (`GoogleImageProxy`), and a
    proxy fetch isn't a reliable signal of a human actually viewing the
    email regardless.
  - Proton Mail's UI explicitly reporting it blocked
    `/track/pixel/<code>.gif` — this is Proton's own tracker-blocking
    feature, a deliberate recipient privacy choice, not a bug and not
    something to work around.
  - Click count showing 13 instead of an expected 10 (5 Proton + 5 Gmail)
    — confirmed via raw `signature_clicks` rows that two clusters of
    extra clicks (4 in Firefox ~1 second apart, 4 in a different Chrome UA
    seconds later, both missing the same platform) landed shortly after
    the Gmail send. Pattern matches an automated link-scanner rendering
    each link in a real browser before/on open — a known industry-wide
    click-tracking limitation, distinct from the Gmail-proxy case since
    there's no self-identifying user-agent to exclude the same way.
    Logged as a known limitation; a burst-detection heuristic was
    considered and deliberately not implemented yet, since a fast genuine
    human clicking several links back-to-back would look identical, and
    getting this wrong risks undercounting real engagement — worth its
    own dedicated design pass if pursued.
Also confirmed via Firefox's Inspector on the actual signature saved
inside Outlook's editor that the social icons render "connected" there:
compared against the app's own "Copy HTML" output and confirmed the app's
generated HTML is correct (each icon has its own `margin-right:4px`) —
Outlook's own paste-sanitizer wraps adjacent same-background-color
elements in an extra `<span class="spanWithBackgroundColor">` that paints
solid color across the gaps. Diagnosed but not yet fixed — real fix
requires rebuilding `social_html` as a table-based layout (more reliable
across Outlook's paste-cleanup than inline-block + margin), which touches
all 8 call sites across all 9 layout branches in `_generate_html_content()`
and needs its own dedicated pass. `pytest` (91 passed), `ruff check .`,
`ty check .` all clean after the pixel fix.

## 2026-08-02 (cont.): Solid/Split live visual verification
Closed the last open verification gap from the 2026-07-26 layout session:
visited the live production URL and confirmed both the `solid` and `split`
Pro-tier layouts render as intended with a real signature. No code changes
needed.

## 2026-08-02: Fix ProductionConfig import-time crash (CI had been broken since 2026-08-01)
Discovered via `gh run list` that CI had been failing on every push since the
`SECRET_KEY`/`BREVO_FROM_EMAIL` production guards were merged the previous
session — including both of that session's own runs, which were never
actually checked at the time. Root cause: `ProductionConfig`'s class body
called `get_secret_key_for_config("production")` directly as a class
attribute assignment, which executes immediately whenever `app.config` is
imported — not only when `ProductionConfig` is actually used to start an
app. Since `app/__init__.py` imports `app.config` unconditionally, every
test run and CI job evaluated `ProductionConfig`'s body and raised, even
though the app was never actually running in production mode. It only
appeared to work locally because the local `.env` happens to have
`SECRET_KEY` set, masking the bug. Fixed by moving the validation into a
`ProductionConfig.init_app(app)` hook (Flask's standard pattern for this),
which only runs when a config is actually applied to a real app via
`create_app()` — not at import time. `ProductionConfig`'s class attributes
now read the env vars directly without raising; `Config.init_app()` is a
no-op that subclasses can override, so `DevelopmentConfig`/`TestingConfig`
are unaffected. Corrects an inaccurate claim in this file's 2026-08-01
entry and in `PROJECT_STATUS.md`: CI was not actually confirmed passing
after that session's guards were added, despite what was recorded at the
time. `pytest` (91 passed), `ruff check .`, `ty check .` all clean, and
`gh run list` now shows a genuine green run on GitHub Actions for the
first time since the guards were introduced.

## 2026-08-01 (cont. 2): Audit triage — tracking.py and signatures.py exception narrowing
Completed the pass-1 audit triage: reviewed `app/routes/tracking.py`'s
`pixel()`/`click()` and `app/routes/signatures.py`'s `create()`/`edit()`,
all four of which caught broad `Exception` and continued (serving the GIF,
redirecting, or showing a generic error) rather than surfacing failures.
The graceful-continue behavior itself was correct by design — a public
tracking endpoint must never break a recipient's inbox rendering over an
analytics write failure, and both routes' docstrings already documented
this intentionally — but catching bare `Exception` meant an unrelated
programming bug would be silently swallowed forever alongside legitimate
database failures. Narrowed all four `except Exception:` blocks to
`except SQLAlchemyError:` in both files, so real database failures are
still handled gracefully exactly as before, while any other bug now
surfaces as a real error instead of vanishing into a log line. This also
fixed a related latent bug in `signatures.py`: `update_signature()` calls
`get_signature_by_id()` internally a second time (`edit()` already fetches
it once, outside the `try` block), which can raise Werkzeug's `NotFound`
on a delete-during-edit race condition — previously that 404 would have
been caught by the bare `except Exception:` and shown as a generic "an
error occurred" flash instead of a proper 404 page. Reviewed
`app/routes/signatures.py`'s form-handling duplication finding and found
it largely already resolved: `_read_signature_form_fields()` already
exists as a shared helper for both routes; the remaining shared shape
(validate → extract fields → try/except/flash/redirect) was judged not
worth extracting further with only two call sites and real differences
between them (rule of three — revisit if a third caller appears).
`pytest` (91 passed), `ruff check .` (all checks passed), `ty check .`
(all checks passed) confirmed clean after both files. This closes out the
full pass-1 audit: all five items are now either fixed and verified, or
reviewed and deliberately deferred with documented reasoning.

## 2026-08-01 (cont.): Audit triage — user.py fixes
Triaged the remaining `docs/AUDIT_FINDINGS.md` items by confidence level.
Fixed two: `is_locked()` was mutating state (clearing lockout fields and
committing) as a side effect of what should be a pure read-only guard
check — split into a pure `is_locked()` and a new `clear_expired_lockout()`
that persists the reset. This uncovered a latent bug: `record_failed_login()`
never checked for an expired lockout before incrementing, so a user's first
failed attempt after their lockout window ended could instantly re-lock
them off a stale attempt count; `record_failed_login()` now calls
`clear_expired_lockout()` first. Also extracted a shared `_token_is_valid()`
static helper for `verify_email()`/`reset_password()`, which had duplicated
the same token-match-and-expiry check. Reviewed the
`record_failed_login()`/`record_successful_login()` persistence-in-model
finding and deliberately deferred it — every other method in the file
follows the same commit-in-model convention, so fixing only two would make
the file inconsistent rather than cleaner; a real fix means moving
persistence into a service layer project-wide. `pytest` (91 passed),
`ruff check .`, `ty check .` all clean, including after catching and
removing an accidental duplicate `record_failed_login()` definition
introduced mid-edit.

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
Extracted a `_build_html_content(signature)` helper in
`signature_service.py` so `create_signature()`/`update_signature()` share
one source of truth for the 14 fields that feed HTML generation, instead
of each listing them separately; also removed a stray leftover comment
found alongside it. Ran the project's first full pass-1 codebase audit
against `docs/signs-of-llm-generated-code.md`, covering every git-tracked
file; findings logged in `docs/AUDIT_FINDINGS.md` for future triage.
Checked one audit finding (`terms.html`/`base.html` contact copy vs.
`privacy.html`) and confirmed it was a false positive — no fix needed.
Flagged a new, separate concern: `BREVO_FROM_EMAIL` is a personal Outlook
address, not a Brevo-authenticated domain, which is a deliverability risk
tied to the existing custom-domain decision, not a code bug. Test suite:
91 tests, all passing throughout every fix. `ruff check .` clean
throughout. `ty check .` clean throughout. Deployed and confirmed live:
email verification, email change, password change, and account deletion
all tested working on the production site, along with every other form
in the app.

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