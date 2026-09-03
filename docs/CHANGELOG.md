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

## 2026-09-02: Playwright e2e test suite, CI hardening, disposable Postgres for CI
Added a 5-test Playwright suite under `tests/e2e/` covering login
(valid/invalid credentials), signature creation and confirmation, an IDOR
regression test for cross-account signature access (pairs with the
ownership filtering already in `analytics_service.py` and
`SignatureService.get_signature_by_id`), a downgrade-locks-paid-feature
test that simulates a Stripe webhook tier change without a real Stripe
call, and a regression test for the previously-fixed stored-XSS
vulnerability in `_sanitize_accent_color` (malformed accent_color values
attempting to break out of a style="" attribute now correctly fall back
to the default rather than being interpolated raw).

Added `tests/e2e/conftest.py`: fixtures that create and tear down real
database rows (`user_a`, `user_b`, `pro_user`, `signature_b`), plus a
`set_subscription_tier()` helper. Added `playwright==1.62.0` and
`pytest-playwright==0.9.0` to `requirements.txt`.

Updated `.github/workflows/ci.yml`'s `e2e` job to spin up a disposable
`postgres:16` service container scoped to the job's lifetime, rather than
connecting to the Neon `dev` branch — real Postgres engine preserved
(avoiding the SQLite naive/aware-datetime parity issue documented in
`user.py`), but with zero dependency on, or risk to, any persistent
database. Added a `flask db upgrade` step for the empty container, fixed
a readiness-loop bug that would have silently passed even if the Flask
server never started, added job-level `timeout-minutes` to prevent a
hung Playwright run from sitting on a runner for hours, and added
`permissions: contents: read` at the workflow level.

Two initial CI runs failed with `playwright: command not found` — root
cause was that `tests/e2e/` and the updated `requirements.txt` had only
ever existed locally, never committed. Not a workflow or dependency
defect. Committing both resolved it; confirmed via `gh run list`: all
108 tests (102 existing unit tests + 6 new e2e tests) passing in CI
against the disposable container.

---

## 2026-08-08: CTR capped at 100%, link count added, gunicorn control-socket fix
Resolved the CTR-can-exceed-100% metric-design question flagged in the
2026-08-07 entry. Chose to cap at 100% rather than reframe as "clicks per
open" or count unique opens-with-a-click, since a signature has at most 5
trackable links, making the cap the simplest correct read. Added
`AnalyticsService._calculate_ctr(clicks, opens)` as the single shared
formula, replacing three separate inline calculations in `get_summary()`
(overall and per-signature) and `get_signature_detail()`. Also added
`Signature.link_count`, a property counting how many of `website`,
`linkedin_url`, `twitter_url`, `facebook_url`, `instagram_url` are
actually filled in, and surfaced it on `analytics/detail.html` under the
CTR card so a 100% reading has immediate context.

Separately, root-caused and fixed a recurring but non-fatal Render log
error: `Control server error: [Errno 13] Permission denied:
'/home/appuser'` on every boot. Cause: gunicorn 25.1+ added a control
socket (for the `gunicornc` CLI) enabled by default, which tries to
create a file under `$HOME`; the app's `Dockerfile` runs as `appuser`
with `--no-create-home`, so no home directory exists at all. The app
itself was never affected — the error appeared after gunicorn had
already bound successfully and the service came up live — but it added
log noise on every deploy. Fixed by adding `--no-control-socket` to the
gunicorn `CMD` in `Dockerfile`, since this app doesn't use the runtime
control feature. Deployed and confirmed: the log line no longer appears
on subsequent Render boots.

## 2026-08-07: Fixed Gmail opens showing as 0 (GoogleImageProxy over-filtering)
Root-caused via live Render log capture: a genuine Gmail open request
carries a User-Agent ending in "(via ggpht.com GoogleImageProxy)" —
confirmed directly from production traffic, not just secondhand research.
That exact string had been on `_PROXY_SIGNATURES` since before this
session, originally intended to filter Gmail's automated background
prefetching, but it was silently excluding every real Gmail open too.
Confirmed via a controlled unopened-email test that Gmail is not
currently prefetching this app's tracking pixel in the background — no
request arrived for an email left unread for 5+ minutes — so removing the
exclusion carries no known regression risk today. Removed
`"GoogleImageProxy"` from `_PROXY_SIGNATURES` in `tracking.py`. Left
`"Nexus 5 Build/MRA58N"` in place (unrelated, older Gmail signature).
Added `tests/test_tracking.py` (11 new tests, 91 → 102 total) — the
`pixel()`/`click()` routes and all scanner/proxy filtering had zero direct
test coverage before this session, including the Office 365 Safe Links
fix from 2026-08-06. New tests cover: valid/unknown tracking codes, known
proxy UA exclusion, the Office 365 IP-range check (mocked), and a
dedicated regression test asserting the real GoogleImageProxy UA is now
counted. Verified locally (102 passed, `ruff`/`ty` clean) and live in
both directions: fresh signature, Outlook → Gmail, opened on a phone —
Total Opens correctly read 1 (previously stuck at 0), Total Clicks read 5
with no inflation; Gmail → Outlook also confirmed 1 open / 5 clicks.
Temporary `PIXEL HIT DEBUG` logging added during investigation left in
place for now, in case Gmail's prefetch behavior changes later and needs
to be caught live. Also surfaced a separate, unrelated metric-design
question: CTR (`total_clicks / total_opens × 100`) can exceed 100% when a
recipient clicks multiple platform links per open (e.g. 1 open, 5 clicks
→ 500%) — not a bug, but flagged as an Open Issue to decide the intended
formula.

---

## 2026-08-06: Office 365 Safe Links click-inflation fix deployed
Implemented the IP-range-matching fix drafted on 2026-08-03 (previously
undeployed — see that entry for the earlier `ProxyFix` hop-count mistake).
Added `app/services/ip_range_service.py`, which fetches and caches
Microsoft's published Office 365 IP ranges from `endpoints.office.com` and
exposes `is_office365_ip()`. `tracking.py` now uses a new
`_is_scanner_request()` helper that checks both the existing
`_PROXY_SIGNATURES` User-Agent list and the new IP-range check, since Safe
Links deliberately uses a browser-like User-Agent and can only be caught by
source IP. Added `ProxyFix` to `app/__init__.py` with the corrected
`x_for=1, x_proto=1` (this app has one proxy hop — Render's load balancer —
no Cloudflare, since no custom domain is configured); required a
`typing.cast(Any, ...)` on the `wsgi_app` reassignment to satisfy `ty`,
since Werkzeug's stubs type `wsgi_app` as a bound method and can't verify
`ProxyFix`'s wrapper satisfies the same runtime contract. Added an autouse
`conftest.py` fixture keeping the Microsoft endpoint fetch out of test
runs. Verified locally: 91 tests passed, `ruff` and `ty` clean, and
`is_office365_ip()` manually confirmed against one real Microsoft IP
(`40.92.0.1` → True) and one unrelated IP (`8.8.8.8` → False) before
deploy. Deployed via push to `main`, CI green.

Live-tested end-to-end with a real signature: sent Outlook → Gmail and
Gmail → Outlook, clicked all 5 platform links each way — Link Clicks
counted correctly with no inflation in both directions. Note: this
specific test didn't route through an actual Office 365 recipient mailbox,
so it confirms normal click accuracy but hasn't yet directly exercised the
Safe Links-filtering code path itself; that needs a test with an Office
365-hosted recipient specifically.

Also surfaced a separate, likely pre-existing bug during this same test:
**Total Opens stays at 0 for Gmail recipients regardless of whether they
open the email**, because Gmail routes all image loads (both automatic
prefetch and genuine "Show images" clicks) through Google's own
image-caching proxy, whose User-Agent contains `GoogleImageProxy` — a
string already on `_PROXY_SIGNATURES` specifically to filter Gmail's
background prefetching. The filter can't currently distinguish a real
Gmail open from an automated one, since both produce an identical request.
Confirmed via a controlled test: Outlook → Gmail showed 0 opens; Gmail →
Outlook correctly incremented opens by 1. Tracked as a new Open Issue —
investigation not yet started.

---

## 2026-08-05 (cont.): Bumped cryptography 48.0.1 → 50.0.0, clearing 3 CVEs
Docker Scout flagged 46 vulnerabilities in `signature-app:latest`; nearly
all of them (`perl`, `tar`, `util-linux`, `glibc`, `systemd`, `coreutils`,
`sqlite3`, `shadow`, `apt`, `diffutils`, `openssl`) were unfixed
Debian-trixie base-image CVEs with no available patched version — not
actionable, and not reachable via this app's code paths. The one real,
fixable item was `cryptography 48.0.1`: CVE-2026-69249 (HIGH, fixed in
49.0.0), CVE-2026-69247 (HIGH, fixed in 50.0.0), and CVE-2026-69248
(MEDIUM, fixed in 49.0.0). Bumped `requirements.txt` to
`cryptography>=50.0.0`. Verified locally before touching Docker: 91 tests
passed, `ruff check .` clean, `ty check .` clean. Rebuilt the image and
re-scanned — package count went 161 → 170 from the dependency bump, and
vulnerability count dropped 46 → 43, exactly the three `cryptography`
CVEs cleared with nothing else changed. Deployed via push to `main`
(CI green). Remaining 43 vulnerabilities are all unfixed Debian
base-image CVEs, tracked but not actionable until Debian ships patches.

---

## 2026-08-05: Celery + Redis explored for resume purposes, fully reverted
Explored adding Celery and Redis to the project — motivation was purely
resume/interview signal (entry-level backend role), not fixing a bug or
gap. Built a complete, working local integration in small verified steps:
a Redis instance via Render's Key Value service (confirmed genuinely free
at the Starter/25MB tier, directly from `render.com/pricing`); a minimal
`app/celery_app.py` pointing at it; `app/tasks.py` with three task
wrappers around the existing `email_service.py` functions, using deferred
imports inside each task specifically so the existing
`tests/conftest.py` `mock_email_sends` patches would keep working
unchanged; all five call sites that send email
(`user_service.register_user`, `auth.register`, `auth.forgot_password`,
`auth.resend_verification`, `profile.change_email`) switched from calling
`email_service.send_*` directly to `app.tasks.send_*_task.delay(...)`;
and a `celery_eager_mode` autouse pytest fixture (`task_always_eager`) so
the test suite never opens a real connection to Redis. All 91 tests
passed with the full integration in place, `ruff` and `ty` clean.

Hit a real, verified cost wall trying to make it run live in production:
Render's free compute tier covers web services, Postgres, and Key Value
(Redis) — but **not** background workers, which start at $7/month on any
plan, confirmed directly against `render.com/pricing` and
`render.com/docs/free`. (An earlier claim in this same session that
background workers had a free tier too was wrong — based on misreading a
pricing table row that covered three service types together; corrected
once the person hit it directly in their own Render dashboard.)

Investigated a free workaround: running the Celery worker as a background
thread inside the existing free web service process, instead of a
separate paid worker service. Tested directly rather than assuming it
would work, and found it genuinely unsafe: `celery_app.Worker(...).start()`
called from a non-main thread silently kills the entire host process the
moment it starts — Celery's worker assumes it owns the whole process,
including installing OS signal handlers, which only works on Python's
main thread. Confirmed reproducible in a sandbox test (banner prints,
then the whole interpreter exits mid-script with no exception surfaced).
The one variant that did work safely, `celery.contrib.testing.worker.
start_worker`, is an internal Celery testing helper, not intended or
appropriate for production use — so not something to build the real
feature on.

With no free way to run it live, and running only in local dev not being
a real deliverable, decided to fully revert rather than ship a half
integration: deleted `app/celery_app.py` and `app/tasks.py`, restored the
original direct (non-async) email-sending code at all five call sites,
removed the `celery_eager_mode` fixture from `tests/conftest.py`, removed
`celery` and `redis` from `requirements.txt`, removed `REDIS_URL` from
both `.env` and the Render web service's environment variables. `pytest`
(91 passed), `ruff check .`, `ty check .` all clean; deployed and
confirmed working — the app is functionally identical to before this
session. The `app/__init__.py` `ProxyFix` change explored in the earlier
click-count session (2026-08-03) was never applied to the repo either
(see that entry) — unrelated to this revert, just confirming it's not
something to look for. A free `signature-redis` Key Value instance may still exist on
the Render dashboard, unused but costing nothing; left as an open,
no-action-needed decision for the person to delete or keep.

---

## 2026-08-03: Click-count scanner filtering explored, not deployed; ProxyFix hop-count corrected on paper
Investigated the click-count inflation issue (see Open Issues): identified
the root cause as Microsoft Defender for Office 365 Safe Links performing a
pre-delivery "preliminary scan" that visits every link in an email using a
browser-like User-Agent specifically designed to blend in, meaning the
existing `_PROXY_SIGNATURES` User-Agent substring list (which already
catches Proofpoint and Barracuda) cannot catch it — the only reliable
signal is the request's source IP. Drafted a fix: a new
`app/services/ip_range_service.py` that fetches and caches Microsoft's
publicly published Office 365 IP ranges (`endpoints.office.com`), used from
`tracking.py`'s `click()` route to log-and-exclude matching clicks
separately from the existing proxy-UA exclusion; a corresponding autouse
pytest fixture to keep the outbound HTTP call out of CI; and a `ProxyFix`
addition to `app/__init__.py`; since this app sits behind Render's reverse
proxy and `request.remote_addr` would otherwise show Render's own IP for
every request, not the real client. **None of this was applied to the
repo** — the person found the change too complex to take on confidently,
and asked for a plain-language explanation instead of the code.

That review surfaced a real mistake in the drafted `ProxyFix` config: it
was set to `x_for=2, x_proto=2`, assuming a two-hop chain (Cloudflare, then
Render's load balancer). That two-hop chain only exists once a custom
domain is routed through a customer's own Cloudflare account — Render's
default `*.onrender.com` subdomain (what this app's live URL actually is;
no custom domain is configured yet) talks directly to Render's load
balancer with no Cloudflare involved at all. Confirmed via Render's own
docs and a real user report describing this exact gap as a bypass path
around a separately-configured Cloudflare zone. The correct setting for
this app's current deployment is `x_for=1, x_proto=1` — trusting only
Render's own hop. Had the original `x_for=2` version shipped, it would
have let an attacker prepend a fake IP in `X-Forwarded-For` and have it
trusted as the real client address, since the real hop count (1) was
lower than what was configured (2). No code was affected in production;
this was caught and corrected before anything was deployed. If a custom
domain + Cloudflare is added later, this hop count needs to be revisited.

Separately, closed three open issues by decision rather than code change:
old relative tracking URLs (resolved — old signatures using them were
deleted), the clipboard-copy regression test (declined — the underlying
bug is already fixed and browser-automation tooling wasn't judged worth
adding just for this), and the remaining low-priority audit styling notes
(`record_failed_login()`/`record_successful_login()` committing directly
to the DB, `tracking.py`'s hardcoded platform-mapping dict, and
`app/__init__.py`'s monolithic `create_app()`) — accepted as-is.

---

## 2026-08-02 (cont. 6): Table-based social icon layout fixes Outlook icon-joining bug
Fixed the social-icon "connected" rendering in Outlook diagnosed in the
previous session (cont. 4): confirmed via Firefox Inspector that
`signature_service.py`'s generated HTML was correct on the app's side —
each icon `<a>` had its own `margin-right:4px` — but Outlook's own
paste-sanitizer wraps adjacent same-background-color inline elements in
an extra `<span class="spanWithBackgroundColor">` once the HTML is pasted
into a New Outlook / Outlook on the web signature field, painting solid
color across the gaps between icons regardless of the source margin.
Replaced the inline-block `<a>` + margin pattern with a new shared
`_build_social_table()` static method that renders each icon as its own
`<td>` cell in a small `<table>`, with a dedicated zero-width spacer `<td>`
between icons instead of margin — table cells are structurally separate
elements the sanitizer has nothing to coalesce. Applied to both places
the app builds social icon HTML: the shared block reused by 8 of the 9
signature layouts (`classic`, `modern`, `minimal`, `ruled`, `avatar`,
`compact`, `banner`, `split`), and the `solid` layout's separate
white-background/accent-text variant, which had duplicated the same
inline-block pattern rather than reusing the shared one. No changes to
`_sanitize_href()`, the tracked-click URL construction, or any
escaping/validation — this was purely a markup-structure fix, not a
security or data change. `pytest` (91 passed), `ruff check .`,
`ty check .` all clean locally before deploy. Deployed; confirmed green
via `gh run list`. Verified live in both Outlook and Gmail on the actual
deployed site: social icons now render as separate rounded badges, no
longer merged into one solid-color block.

## 2026-08-02 (cont. 5): Fix production AttributeError from an incomplete commit
`validate_logo_url()` caused a live 500 on `/signatures/<id>/edit` —
`AttributeError: type object 'SignatureService' has no attribute
'validate_logo_url'` — despite passing locally. Root cause: the method was
added to `app/services/signature_service.py` as part of the same fix that
added its call site in `app/routes/signatures.py`, but a subsequent
`ty`-narrowing fix only staged and committed `signatures.py`, never
`signature_service.py`. Local tests kept passing because the local
working copy still had both files; CI and production build from what's
actually committed, so both failed identically once `signatures.py` tried
to call a method that had never been pushed. Fixed by committing the
missing file. Confirmed live: submitting an SVG logo URL on the deployed
site now correctly shows the flash warning instead of a 500. Lesson: when
a fix spans multiple files, every `git add`/commit for that fix must
include all of them together, even in follow-up commits addressing a
linter/type error on just one of the files.

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