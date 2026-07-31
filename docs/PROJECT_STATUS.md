# Signature — Project Status

*This file replaces the old `HANDOFF_N.MD` habit. It is edited in place, not
appended to — when something here gets done, it's deleted, not moved to a
"done" list. Git history is the permanent record; this file is only ever a
snapshot of "true right now." Paste this whole file at the start of a new
chat.*

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
- Test suite: 86 tests, all passing. `ruff check .` clean. `ty check .`
  surfaces 4 warnings (Flask-SQLAlchemy `db.Model` MRO resolution — see
  Open Issues); confirmed unrelated to `ty` version and to this session's
  changes.
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
- [ ] **`ty` MRO warnings on `db.Model` subclasses** — `ty check .` surfaces
      4 warnings (`analytics.py` x2, `signature.py`, `user.py`) about an
      unresolved MRO for classes inheriting Flask-SQLAlchemy's
      dynamically-generated `db.Model` base. Confirmed NOT a version-drift
      issue (`pip show ty` = `0.0.61`, matching the pin). Most likely a
      known false-positive class with Flask-SQLAlchemy's declarative
      metaclass that predates this session and simply wasn't noticed
      before, since it's a warning, not a failing check. No code change
      caused this. Decide whether to silence it (inline `# ty: ignore` or
      config exclusion) or leave as background noise.
- [ ] **Outlook/Apple Mail delivery test** — the create → copy → paste →
      send → receive flow has only been validated in Gmail. UI install
      instructions exist for all three clients, but Outlook/Apple Mail
      haven't been tested end to end.
- [ ] Consider a regression test or manual QA checklist item for the
      clipboard-copy background bug (fixed in an earlier session)
- [ ] Existing signatures created before a certain point have old relative
      tracking URLs (data issue, not a code bug)
- [ ] Placeholder emails in `terms.html`/`privacy.html` not yet replaced
      with real ones
- [ ] `font_family`'s Pro-only set intentionally isn't validated beyond the
      allow-list check — no further action needed, just noting the design
      is deliberate (see Recently Completed below)
- [ ] Decide whether to keep `app/static/css/output.css` committed to git or
      remove it (add to `.gitignore`) now that Docker rebuilds it fresh on
      every image — either is fine, just an open decision

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
- Brevo domain authentication decision — tied to the domain purchase above
- Auto-regenerating `html_content` on Stripe webhook tier change — decided
  against, watermark/font/color only update on next manual save

---

## Recently Completed (this section gets replaced, not appended, next session)

**Session: Solid and Split layout templates (2026-07-26)**
- Added two new Pro-tier layouts: `solid` (full solid-color card, white
  text) and `split` (colored avatar rail + white content column). Both
  added to `SignatureService.PRO_LAYOUTS` and given their own
  `_generate_html_content` branches, mirrored into the Alpine.js live
  preview in `create.html`/`edit.html`, and given matching layout-picker
  tiles
- Found and fixed two small pre-existing bugs in `edit.html`'s `avatar`
  layout preview (missing department line; logo `<img>` missing sizing/
  object-fit) while working in that file — unrelated to the new layouts
- Added 8 tests to `test_signatures.py` (free-tier fallback, Pro-tier
  access, edit persistence, downgrade case — for both new layouts). Test
  suite: 78 → 86, all passing. `ruff check .` clean
- `ty check .` surfaced 4 pre-existing warnings unrelated to this session
  (see Open Issues) — not yet investigated or resolved
- Pushed to `main`. CI green, Render deploy green. Live visual check of the
  two new layouts still outstanding (see Open Issues)
- Also untracked `tests/__pycache__/*.pyc` (was accidentally committed) and
  added `!docs/CHANGELOG.md` to `.gitignore`'s `docs/*` negation pattern,
  same fix as the `PROJECT_STATUS.md` one from the prior session

*Earlier sessions' full detail now lives in `CHANGELOG.md` — this section
was trimmed back per the ~150-line guideline below.*

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