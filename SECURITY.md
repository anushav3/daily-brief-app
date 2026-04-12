# Security Best Practices

This document covers the security model for the Daily Brief agentic app and the rules to follow when extending or running it.

---

## Secrets management

| What | Rule |
|------|------|
| Gmail App Password | Always via `GMAIL_APP_PASSWORD` env var — never hardcoded |
| Email addresses | Always via `EMAIL_TO` / `EMAIL_FROM` env vars — never hardcoded |
| Any new credential | Same pattern: `os.environ.get("VAR_NAME", "")` |

**Never commit secrets.** The `.gitignore` excludes `.env*` files. If you add a `.env` file locally for convenience, confirm it is gitignored before every commit.

If a secret is accidentally committed, rotate it immediately — git history is public even after a force-push.

---

## Environment variable setup (local)

```bash
export EMAIL_TO='you@gmail.com'
export EMAIL_FROM='you@gmail.com'   # optional, defaults to EMAIL_TO
export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'
```

For persistent setup without committing secrets, add the exports to `~/.zshrc` or `~/.bashrc` (not to any file inside this repo).

---

## Gmail App Passwords vs account password

- Use an **App Password**, not your Gmail login password.
- App Passwords are scoped to a single app and can be revoked individually without changing your main password.
- Requires 2-Step Verification to be enabled on the Google account.
- Revoke at: Google Account → Security → App passwords.

---

## External fetch surface

The script fetches from these external URLs at runtime:

| Destination | What |
|-------------|------|
| `tldr.tech` RSS feeds | AI, infosec, startups, product news |
| `aidailybrief.beehiiv.com` | AI Daily Brief (HTML scrape) |
| `npr.org` RSS | Up First podcast feed |
| `query1.finance.yahoo.com` | Stock chart data |
| `smtp.gmail.com:465` | Outbound email delivery |

**Rules:**
- All fetches use a read-only `GET` with a generic `User-Agent`. No credentials are sent to any of these endpoints.
- TLS verification is relaxed (`CERT_NONE`) to handle CDN edge certs. If you harden this, test each feed individually.
- RSS content is rendered into email HTML. Strip all HTML from feed descriptions (already done via `strip_html()`) to prevent XSS in the preview file.
- Never pass feed content to a shell command or `eval`.

---

## Output files

| File | Risk | Mitigation |
|------|------|------------|
| `daily_brief_preview.html` | Contains external links from RSS feeds | Gitignored — never committed |
| `dashboard.html` | Static local file | No server-side execution; safe to open locally |

---

## Agentic coding agent rules

When a coding agent (Claude Code, Cursor, etc.) modifies this repo:

1. **No secrets in code.** Reject any diff that hardcodes an email address, password, token, or API key.
2. **No `shell=True` or `subprocess` calls** unless explicitly required and reviewed.
3. **No new outbound endpoints** without updating this document and the CLAUDE.md feed table.
4. **No `eval()` or `exec()`** on external content.
5. **Preview before push.** Run `python3 daily_brief_email.py` to generate the preview and verify output before committing.
6. **Keep `.gitignore` current.** Any new output file or local config should be added to `.gitignore` before the first commit.

---

## Dependency hygiene

This script uses only Python stdlib — no `pip install` required. This minimises supply-chain risk. Before adding any third-party dependency:
- Confirm it cannot be replaced with stdlib.
- Pin to an exact version.
- Add to this document with justification.
