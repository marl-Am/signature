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
  rollout has created two possible menu paths. **Outlook end-to-end
  delivery (install → send → receive → opens/clicks tracking) is now
  fully tested and confirmed working**, following a real bug fix (see
  Recently Completed). Apple Mail testing is still outstanding.
- **The full pass-1 code audit (`docs/AUDIT_FINDINGS.md`) is now fully
  triaged and closed out**, and every fix from this session is confirmed
  live in CI (not just locally) — see Recently Completed and
  `CHANGELOG.md` for the complete history.
- `SECRET_KEY` and `BREVO_FROM_EMAIL` production guards deployed and
  confirmed live: email verification, email change, password change, and
  account deletion all tested working on the production site.

---

## Open Issues


- [ ] **Social icons render "connected" in Outlook** — confirmed via a
      live test: the app's generated HTML is correct (each icon has its
      own `margin-right:4px`), but Outlook's own paste-sanitizer wraps
      adjacent same-color icons in an extra `<span>` that paints solid
      color across the gaps. Real fix is rebuilding `social_html` as a
      table-based layout instead of inline-block + margin — touches all
      9 layout branches in `_generate_html_content()`, needs its own pass.
- [ ] **Click counts inflated by automated link-scanners** — confirmed via
      raw `signature_clicks` rows that some providers' security scanners
      visit every link in a real browser before/on open, adding phantom
      clicks with no reliable self-identifying signal (unlike the
      Gmail-proxy case, already handled). Known industry-wide limitation,
      not fixed — a burst-detection heuristic was considered and
      deliberately deferred, since a fast genuine human clicking several
      links back-to-back would look identical, and getting it wrong risks
      undercounting real engagement.
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

**Session: live Outlook delivery test + fixes (2026-08-02)**

- Ran a full live delivery test in New Outlook / Outlook on the web,
  sending to both Proton Mail and Gmail, and cross-checked results against
  the Analytics dashboard and raw Neon rows.
- Fixed a real bug found by this test: the tracking pixel's
  `style="display:none;"` caused Outlook/Microsoft 365 to silently skip
  fetching it as a known tracking heuristic. Removed `display:none`;
  confirmed opens now record correctly after re-saving and re-testing.
- Fixed a second real bug: logo URLs pointing to an SVG rendered as
  nothing in every tested client, with no error or broken-image
  indicator. Added `_sanitize_image_href()` (backend backstop) and
  `validate_logo_url()` (user-facing flash message) so an SVG logo is now
  explained and blocked at save time instead of silently invisible.
- Triaged three further observations and confirmed each is expected
  client behavior, not a bug: Gmail's image-proxy holding opens at 1
  (already handled by the existing `_PROXY_SIGNATURES` exclusion), Proton
  Mail's own tracker-blocking feature, and automated link-scanners
  inflating click counts (a known, deliberately-unaddressed industry-wide
  limitation — see Open Issues).
- Diagnosed (not yet fixed) the social-icon "connected" rendering in
  Outlook: confirmed via Firefox Inspector that the app's own generated
  HTML is correct, and the cause is Outlook's paste-sanitizer wrapping
  same-color icons in an extra span. Real fix needs a table-based layout
  across all 9 signature layouts — see Open Issues.
- `pytest` (91 passed), `ruff check .`, `ty check .` all clean after every
  fix, including a `ty` type-narrowing fix in `signatures.py` (checking
  `logo_error` directly rather than the paired bool before `flash()`).
- Older completed sessions (audit triage, ProductionConfig import-time
  fix, Solid/Split visual confirmation) have moved to `CHANGELOG.md`.
---

## Next Up

- [ ] Rebuild `social_html` as a table-based layout across all 9 signature
      layouts to fix Outlook's paste-sanitizer collapsing icon spacing.
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