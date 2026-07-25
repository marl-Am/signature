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
  fixed accent color, watermark included.
- Pro tier: unlimited signatures, all 11 fonts, custom accent color, no
  watermark, priority support.
- Test suite: 72 tests, all passing. `ruff check .` and `ty check .` both
  clean as of the last run.
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
- [ ] Confirm the live production URL renders styling correctly after the
      Tailwind Docker build migration (verified locally via `docker build` +
      `docker run` on `localhost:5000`, not yet re-confirmed on the deployed
      URL)
- [ ] Decide whether to keep `app/static/css/output.css` committed to git or
      remove it (add to `.gitignore`) now that Docker rebuilds it fresh on
      every image — either is fine, just an open decision

**Cheap Pro-tier design features not yet built** (same gating pattern as
accent color/font family — form field → route passes through unconditionally
→ service layer enforces tier + validates input):
- [ ] Divider/border style options (easiest)
- [ ] Avatar shape variants (easy)
- [ ] More layout templates (moderate effort, no new dependencies)
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

**Session: .gitignore/.dockerignore audit (2026-07-25)**
- Audited `.gitignore` and `.dockerignore`; confirmed `node_modules/` and the
  stray shell-redirect filenames (`tatus`, `status`) were already correctly
  excluded in both files — no action needed there
- Found and fixed a real bug: `.gitignore`'s `docs/` and bare `docs` patterns
  excluded the directory itself, which silently disables any later `!`
  negation pattern for files inside it (a documented Git limitation — parent
  directory exclusions are never traversed, so re-inclusion rules never
  evaluate). `docs/architecture.md` happened to already be tracked so this
  hadn't caused a problem yet, but a future `git rm --cached` + re-add, or a
  fresh clone attempt, would have silently failed to re-include it. Fixed by
  changing the pattern to `docs/*` (excludes contents, not the directory
  itself) paired with `!docs/architecture.md`, and removing the bare `docs`
  line, which had the same problem
- Confirmed via `git ls-files` that `docs/architecture.md` is tracked and
  safe

**Session: landing page overhaul, Tailwind build migration, Outlook doc accuracy, repo cleanup (2026-07-25)**
- Replaced the fake testimonials section on the landing page with a live
  interactive signature demo (name/title/company/phone/email/accent color,
  Alpine.js `x-model`/`x-text` only — no `x-html`, no injection surface) and
  a clearly-labeled "sample data" analytics preview matching the real
  `/analytics` page's card and chart styling
- Migrated Tailwind CSS off the CDN's in-browser JIT compiler: added
  `tailwind.config.js`, `input.css`, and `package.json` (`build:css` /
  `watch:css` scripts); updated `base.html` to link the compiled stylesheet
  instead of the CDN `<script>` + inline config block
- Added a third Docker build stage (`frontend-builder`, `node:20-slim`) that
  runs `npm ci` + `npm run build:css` during the image build and copies only
  the compiled `output.css` into the runtime stage — Node/npm never ship in
  the final image, same discard-the-toolchain pattern as the existing Python
  builder stage
- Verified locally: `docker build` completed clean (33/33 steps), `docker
  run` on `localhost:5000` confirmed correct styling end to end
- Checked the Outlook and Apple Mail install instructions on the preview
  page against current documentation; Apple Mail and Classic Outlook desktop
  were already accurate, New Outlook/web was updated to branch for both
  menu paths Microsoft's ongoing UI rollout currently produces
- Repo cleanup: confirmed the stale `test-workflow` branch no longer exists
  locally or on the remote (already deleted); deleted unused
  `requirements-dev.txt` after confirming nothing in code, CI, or the
  Dockerfile referenced it; discovered `ty` had only ever been installed via
  that now-deleted file and added `ty==0.0.61` to `requirements.txt` so a
  fresh clone still has everything `README.md`'s setup instructions promise;
  fixed `README.md`'s stale test count (62 → 72), stale XSS-coverage wording,
  stale Tailwind/CDN description, and removed the now-invalid
  `requirements-dev.txt` install step

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