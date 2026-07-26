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
- Pro tier: unlimited signatures, all 11 fonts, custom accent color, all 7
  layout templates, no watermark, priority support.
- Test suite: 78 tests, all passing. `ruff check .` and `ty check .` both
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

**Session: Pro-tier layout template gating (2026-07-25)**
- Found that all seven signature layouts were already fully built and
  rendering correctly, but had zero tier enforcement — any free-tier
  account could select any Pro-only layout directly in the UI. Added
  `FREE_LAYOUTS`/`PRO_LAYOUTS` and `_sanitize_layout()` to
  `SignatureService`, mirroring the existing `font_family` gating pattern
  exactly; free tier is now locked to `classic`
- Locked the six Pro-only tiles in `create.html` and `edit.html` with a
  disabled state, "Pro" badge, and "Upgrade to unlock" note, matching the
  existing accent-color lock UI
- Added six tests to `test_signatures.py` covering free/Pro submission,
  unknown-value fallback, edit persistence, and the downgrade case. Test
  suite: 72 → 78, all passing. Deployed and confirmed live
- Also fixed along the way: `.gitignore`'s `docs/` pattern was silently
  disabling re-inclusion of files inside it (see `CHANGELOG.md` for detail),
  confirmed the Tailwind build renders correctly on the actual deployed URL,
  and tracked `docs/PROJECT_STATUS.md` in git for the first time

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