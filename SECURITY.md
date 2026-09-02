# Security Policy

## Scope
Covers this repo's app, as four separate surfaces:
- the login/registration flow (`src/app.py`'s `register()`/`login()`/`confirm()`);
- the Telegram admin-approval bot (`src/telegram_bot.py`);
- the API-key-authenticated automation-sync endpoint (`POST
  /api/automations/<slug>/sync`, `src/app.py` lines ~556-570) — a third,
  machine-facing auth surface, separate from the session-cookie login above,
  keyed off the per-user `api_key` column in `src/models.py`;
- the GitHub-sync integration (`src/github_sync.py`, invoked by
  `/automations/import-github` and `/automations/<slug>/resync` in
  `src/app.py`). This is **not** part of the login/registration flow despite
  living in the same file — `register()`/`login()`/`confirm()` never call into
  `github_sync`, and reaching it at all already requires an authenticated
  Automator/Admin session (`@automator_required`, plus `User.can_manage` on
  resync) supplying a repo URL. Its own risk is different from auth: it fetches
  and parses README/ROI/SUMMARY/BACKLOG/TODO content from that
  admin/automator-supplied URL (restricted to `github.com`/
  `raw.githubusercontent.com` by `github_sync.REPO_URL_RE`) using `GITHUB_TOKEN`
  — see the Known Limitations entry below for that token and the untrusted-input
  angle.

ClickUp is **not** in scope because there is no ClickUp integration to cover:
`clickup_url` (`src/models.py`) is a plain link a user types into a form, and
`CLICKUP_API_TOKEN` (`.env.example`) is never read by any code in this repo
(`ARCHITECTURE.md` confirms it's "not an active integration"). Does not cover
the other Supplax automations this dashboard links to — report issues in those
in their own repos. For what the login/registration and approval flow actually
do end to end, see `README.md`'s Usage section (`/register` → Telegram notifies
the admin → `/grant`).

## Status: this is live, not a future plan
Earlier drafts of this file called external (beyond-corporate-network) login
access "planned." It has since shipped: the login/registration flow and the
Telegram approval bot are built and in production use (`dashboard/SUMMARY.md`'s
Status field reads "live" — note that field is regenerated from
`docs/functions.md` via `automation-portfolio-sync`, not pulled from deployment
telemetry, so treat it as a self-report, the same epistemic caution given to
`AUTH_SECRET` below. The 2026-09-01 entry in `backlog/BACKLOG.md` says the same
thing, but that isn't independent corroboration: that entry's own text
("перегенерував dashboard/SUMMARY.md і dashboard/functions.md, статус проєкту
змінив на 'Працює'") shows the status field and the backlog note were written
in the same sync edit, not observed separately — so it doesn't add confidence
beyond the self-report itself). This surface is real today — see `PIPELINE.md` §5, which
now carries its own 2026-09-02 correction making this same point: its original
framing ("audience stays internal-only, only the network perimeter is not
trusted") is marked stale there too, not just here, so this file and §5 agree
rather than one lagging the other. The detail both now flag: registration
itself is self-service and open to anyone who reaches `/register`
(`dashboard/SUMMARY.md`: "Завести акаунт може будь-хто" — anyone can create an
account). Access is gated by admin approval *after* signup, not by restricting who
can submit a request, so treat the registration endpoint as public attack surface,
not merely "employees connecting remotely." Separately, `PIPELINE.md` §5 also
flags that this same self-service registration now collects employee personal
data (name, email, department, skills) and that whether this triggers any
compliance obligation is unresolved — this file doesn't answer that question,
it's noted here only because it follows directly from the same feature.

## Supported Versions
| Version | Supported |
|---|---|
| main | yes |

"Supported" means reports against `main` get triaged and, if confirmed, patched by
the project owner — solo maintainer, best-effort, no formal SLA yet. There's no
older release line to backport to.

## Known Limitations
Known gaps identified so far, grouped by component — not exhaustive, and not
capped at one per component:

- **Telegram bot** (`src/telegram_bot.py`): authorizes purely by the incoming
  message's chat ID matching `ADMIN_TELEGRAM_CHAT_ID` — the bot token itself
  carries no separate access control (see the module docstring). The two leaks
  are not equally severe, though: the **bot token** is immediately usable if
  leaked (anyone holding it can call the Telegram Bot API directly — poll
  updates, send messages as the bot), while the **chat ID** alone is not
  spoofable through that API (Telegram sets `chat_id` from the real
  originating chat), so knowing the number does nothing without also
  controlling that actual Telegram account/chat. Either compromise is still
  serious: `/grant <email> admin` (lines 49-65) hands **full `Role.ADMIN` over
  the entire app** to any account named in the command — a materially worse
  outcome than "compromises the approval flow," since it's not just approval
  gate bypass but a direct route to admin-level control of every automation,
  user, department, and skill in the app.
- **GitHub-sync** (`src/github_sync.py`): reads `GITHUB_TOKEN` (`.env`) to call
  the GitHub API on an authenticated Automator/Admin's supplied `repo_url`
  (`/automations/import-github`, `/automations/<slug>/resync` — see Scope
  above). No scope is documented for this token beyond "needed for private
  repos" (`ARCHITECTURE.md`); if it's a broader-scoped PAT than this app
  actually needs, leaking it (logs, error output, the process environment)
  gives an attacker that broader access, not just what this app uses. The
  fetch target itself is constrained to `github.com`/
  `raw.githubusercontent.com` by `github_sync.REPO_URL_RE`, so this isn't an
  open SSRF vector — but the fetched README/ROI/SUMMARY/BACKLOG/TODO content
  is still attacker-influenceable if the supplied repo isn't trusted, and gets
  parsed and stored into `Automation`/`ReviewLogEntry`/`AutomationTodoItem`
  rows; templates don't use Jinja's `|safe` on it (checked), so this isn't a
  known stored-XSS path today, but it hasn't been reviewed as untrusted input
  beyond that.
- **Authorization model / IDOR**: this file scopes the login/registration
  surface but doesn't otherwise describe who can do what once logged in —
  three roles (`Role.ADMIN`/`AUTOMATOR`/`VIEWER`, `src/models.py`) gated by
  `admin_required`/`automator_required`/`User.can_manage` (`src/app.py`).
  Concretely, `/automators/<int:user_id>` (`src/app.py:544-548`) is gated only
  by `@login_required` with no role check, and `automator_profile.html` prints
  `automator.email` directly — so any authenticated user, including a
  self-registered `VIEWER` (the account type `/register` produces by default),
  can enumerate sequential user IDs and harvest every other user's name and
  email. This is a live PII-disclosure path, and it directly feeds the
  compliance question the Status section above raises about self-service
  registration collecting employee personal data.
- **Session cookie has no explicit transport flags**: nothing in `src/app.py`
  sets `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, or
  `SESSION_COOKIE_SAMESITE` (grep confirms none of the three are configured),
  so Flask's defaults apply — notably `SESSION_COOKIE_SECURE` defaults to
  `False`, meaning the cookie isn't marked HTTPS-only. That matters more now
  that the Status section above says this login is reachable beyond the
  corporate network; whether that's accepted risk or an overlooked gap isn't
  documented anywhere in this repo.
- **Login/registration** (`src/app.py`): `SECRET_KEY` (which signs the
  Flask-Login session cookie) is set from `AUTH_SECRET`, but with a silent
  fallback if that env var is missing — `app.config["SECRET_KEY"] =
  os.environ.get("AUTH_SECRET") or "dev-only-insecure-key-set-AUTH_SECRET-in-.env"`
  (line 42) — and no startup check refuses to run without `AUTH_SECRET` set. If
  that fallback is ever what's actually running in prod, sessions are signed with
  a hardcoded key visible in this repo's source, letting anyone forge a valid
  session (login bypass / privilege escalation). This file cannot confirm from
  the repo alone whether `AUTH_SECRET` is set in the live Railway environment —
  verify it there.
- **Login/registration — no rate limiting anywhere** (`src/app.py`,
  `requirements.txt`): `/login` has no lockout or throttle on failed attempts
  (no `flask-limiter` or equivalent is a dependency), so online password
  guessing against a known/enumerable email is unmitigated. `/confirm` is
  worse: the registration code is a 6-digit number
  (`secrets.randbelow(1_000_000)`) valid for 30 minutes, and nothing counts or
  throttles attempts against it — a 1,000,000-value space is brute-forceable
  well inside that window, on the exact endpoint the Status section above
  calls public attack surface.
- **Login/registration — no CSRF protection** (`src/app.py`,
  `requirements.txt`): no `flask-wtf`/CSRF token anywhere in the app.
  State-changing POSTs that run under a logged-in session
  (`/automations/new`, `/automations/<slug>/edit`, department/skill deletes)
  rely on the session cookie alone.
- **API-key sync endpoint** (`POST /api/automations/<slug>/sync`,
  `src/app.py`): authenticated by a per-user `api_key` (`src/models.py:78`,
  `secrets.token_hex(32)`) that never expires or rotates. This key is *not*
  only issued by the admin-run `create_user` CLI: `api_key` is a column
  default, so `/register`'s public, unauthenticated handler
  (`user = existing or User(email=email, role=Role.VIEWER)`, `src/app.py:121`)
  generates a live `api_key` for every self-registered account at signup time
  — before `/confirm`, before Telegram `/grant`, before any admin action at
  all. It sits dormant only because the sync endpoint also requires
  `owner.role in (Role.ADMIN, Role.AUTOMATOR)` (line 569); a single
  chat-ID-gated `/grant <email> automator` (`telegram_bot.py:49-65`) flips that
  role without ever regenerating or displaying the key, silently activating a
  credential the account already held. So this endpoint is one weakly-scoped
  Telegram command away from the same public `/register` surface the Status
  section above calls out as the real risk — not the fully separate,
  admin-CLI-only surface the Scope section's phrasing above suggests.
  Revocation is also narrower than it looks: `/revoke <email>`
  (`telegram_bot.py:66-74`) only sets `is_approved = False`, and
  `api_sync_automation` (`src/app.py:565-570`) never checks `is_approved` —
  only `role` — so a revoked Automator/Admin's `api_key` keeps authenticating
  against this endpoint after `/revoke`, even though the admin who ran it
  would reasonably expect it to cut off all of that account's access. Treat
  any `api_key` (CLI-printed or otherwise) the same as any other
  credential, and don't assume `/revoke` invalidates it.

## Reporting a Vulnerability
Report directly to the project owner. No name or contact is recorded in this repo
yet [placeholder — same unresolved gap as `CODE_OF_CONDUCT.md`'s enforcement
contact]. `SUPPORT.md`'s Telegram channel is also not a real fallback yet — it's
explicitly still a placeholder there too, and this repo only has one Telegram
bot/token defined, so whatever gets stood up there is likely the same bot
infrastructure as the Telegram limitation above — inheriting that access-control
gap rather than being a cleaner alternative.

Until an owner contact exists, use this repo's GitHub Security Advisories
("Report a vulnerability" under the Security tab) *if* private vulnerability
reporting has been turned on for this repo — that's a per-repo GitHub setting
this file (or anything else in the repo) can't confirm from outside GitHub's UI.
If the Security tab doesn't show that option, it hasn't been enabled yet — ask
the owner to turn it on. If you can't reach the owner and GHSA isn't available
either, the least-bad remaining option is a plain GitHub issue, kept to "there's
a vulnerability in `<component>`, contact me for details" with no exploit
specifics or repro steps in the issue body itself, asking the owner to move the
conversation to a private channel from there. That issue is visible to anyone
with repo access, so it's a last resort when the two options above genuinely
aren't available, not a first choice.

When reporting, include what component is affected (login/registration, the
Telegram bot, the API-key sync endpoint, or GitHub-sync — see Scope above),
repro steps, and impact — there's no formal severity rubric yet, so
when in doubt, report it and let the owner triage. (Repro steps and impact go
in the GHSA/owner-contact report itself, not in a public fallback issue — see
above.)

No fixed response-time commitment exists yet. Reporting or testing this app in
good faith won't be treated as an attack.
