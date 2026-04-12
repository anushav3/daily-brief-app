# How to Build: Daily Brief App

A vibe-coded daily email digest that aggregates AI, security, startup news and cybersecurity stock data — built entirely with a coding agent (Claude Code), no manual coding.

---

## What it does

Runs on a schedule → fetches news from RSS feeds + scrapes one site → pulls stock prices from Yahoo Finance → builds a dark-theme HTML email → sends it via Resend API.

**Stack:** Python (stdlib only, zero pip installs) · Vercel · Resend · GitHub · Google Drive · VSCode + Claude Code

---

## Dev Environment: VSCode + Claude Code + Google Drive

### Storage: Google Drive
The entire project lives in a Google Drive folder synced locally via the Google Drive desktop app. This means:
- Files are always backed up automatically
- Accessible from any machine
- No separate backup step before pushing to GitHub

The working directory path looks like:
```
~/Library/CloudStorage/GoogleDrive-.../My Drive/career/daily-brief-app/
```
Git and Vercel work normally from this path — no special setup needed.

### IDE: VSCode + Claude Code

Claude Code is Anthropic's coding agent that runs in your terminal and understands your entire project. Combined with VSCode it becomes your pair programmer.

**Setup steps (no terminal or npm needed):**

1. **Install VSCode** — [code.visualstudio.com](https://code.visualstudio.com)

2. **Install the Claude Code extension:**
   - Open VSCode → Extensions (`Cmd+Shift+X`)
   - Search "Claude Code" → Install (published by Anthropic)

3. **Sign in via the extension UI:**
   - Claude Code panel appears in the **right pane** of VSCode
   - Click Sign In → browser opens → log in with your Anthropic account
   - No npm install, no terminal commands needed

4. **Open your project folder in VSCode** — Claude Code reads the whole codebase automatically

5. **Start building** — type in the right pane. Examples:
   > *"Add a new RSS feed for The Verge AI section to the daily brief"*
   > *"The stock ticker is wrapping on mobile — fix it"*
   > *"Deploy this to Vercel and set up a daily cron"*

**Why VSCode + Claude Code:**
- Claude Code reads your entire codebase for context — not just the open file
- The right pane keeps chat next to your code — no switching windows
- VSCode shows every diff inline before it's accepted
- Can run terminal commands, edit files, and push to git in one session

---

## Step 1: The Script

**Approach:** One Python file does everything — fetch, parse, render, send.

**What worked:**
- Python stdlib only (`urllib`, `xml`, `smtplib`, `json`) — no dependency management
- Yahoo Finance chart API (`query1.finance.yahoo.com/v8/finance/chart/{symbol}`) for stock data — free, no auth
- TLDR Tech RSS feeds for AI / infosec / startups / product news
- NPR Up First RSS for world news headlines

**What didn't work:**
- AI Daily Brief RSS feed (`aidailybrief.beehiiv.com/feed`) — malformed XML caused parse errors every run
- **Fix:** Scrape the `/archive` page instead — it embeds a `window.__remixContext` JSON blob with all post slugs and dates; fetch the latest post page and extract `<p>` tags for article content

---

## Step 2: Email Delivery

Three attempts to send the email.

### Attempt 1 — Gmail SMTP ❌
```
smtplib.SMTP_SSL("smtp.gmail.com", 465)
server.login(email, app_password)
```
**Problem:** Gmail requires an App Password, which requires 2-Step Verification. Some Google Workspace / managed accounts have App Passwords disabled by the admin — no workaround.

### Attempt 2 — Gmail SMTP with App Password ❌
Created an App Password successfully on a personal account, but got:
```
SMTPAuthenticationError: SMTP auth failed
```
The account in use had App Passwords blocked at the account level.

### Attempt 3 — Resend API ✅ (with a fix)
```python
POST https://api.resend.com/emails
Authorization: Bearer re_xxxx
Content-Type: application/json
```
- Free tier: 100 emails/day, no domain verification needed for testing
- Uses `onboarding@resend.dev` as sender out of the box

**Problem hit 1:** Cloudflare 403 error code 1010 (bot block) on Vercel's servers
**Fix:** Add `User-Agent: Mozilla/5.0 (compatible; DailyBrief/1.0)` header to the request

**Problem hit 2:** First email landed in Gmail spam — `onboarding@resend.dev` is an unknown sender
**Fix:** Add `onboarding@resend.dev` to Gmail contacts (saved as "Anusha's Daily Brief") — Gmail trusts contacts and all future emails go straight to inbox

---

## Step 3: Hosting & Scheduling

### Option 1 — Local cron ✅ (simplest)
```bash
crontab -e
# 0 8 * * 1-5 cd /path && EMAIL_TO=x RESEND_API_KEY=x python3 daily_brief_email.py
```
Works, but requires your machine to be on at 8 AM.

### Option 2 — Vercel Serverless ✅
Created `api/send_brief.py` — a Python handler Vercel picks up automatically from the `api/` folder.

**Problems hit:**
1. Vercel detected `requirements.txt` and tried to run `uv lock` for a Python web framework — got `No project table found in pyproject.toml`
   - **Fix:** Delete `requirements.txt` (no dependencies needed anyway)
2. Without `requirements.txt`, Vercel tried to auto-detect a Python web app entrypoint (`app.py`, `main.py`, etc.) — got `No python entrypoint found`
   - **Fix:** Add `"framework": null` to `vercel.json`
3. Cron jobs (`vercel.json` `crons` field) require Vercel Pro for weekday-only schedules (`1-5`)

**Security:** Vercel injects a `CRON_SECRET` env var and sends it as `Authorization: Bearer` on cron requests — handler verifies this to block unauthorized triggers.

### Option 3 — GitHub Actions ✅ (free cron alternative)
Full cron syntax, free on public repos, run history in the Actions tab. Good fallback if Vercel crons need Pro.

---

## Step 4: Design

All CSS lives in `branding-guidelines.md` inside a fenced code block — the script reads and injects it at runtime. This keeps design separate from logic.

**Design choices:**
- New York Times-inspired: serif font, black/white, clean borders
- Dark stock ticker bar (terminal aesthetic) with 2-row layout per ticker (symbol+price / 1d · 1m changes)
- 3-column newspaper grid for news sections
- Each column stacks its 2 sections directly (no CSS grid row alignment) — avoids whitespace gaps between unequal-height cards

---

## Step 5: GitHub + Vercel

```bash
git init && git branch -M main
gh repo create daily-brief-app --public
git add . && git commit -m "initial"
git push
vercel --yes        # links repo, auto-deploys on every push
```

**Security rules added:**
- No email addresses or secrets in code — all via env vars (`EMAIL_TO`, `EMAIL_FROM`, `RESEND_API_KEY`)
- `daily_brief_preview.html` gitignored (contains external links from feeds)
- `SECURITY.md` documents fetch surface, secret handling, and agentic agent coding rules

---

## Environment Variables (all three required to send)

| Variable | Where to get it |
|----------|----------------|
| `EMAIL_TO` | Your email address |
| `RESEND_API_KEY` | resend.com → API Keys |
| `EMAIL_FROM` | Verified sender in Resend (or leave unset to use `onboarding@resend.dev`) |

---

## Alternatives & scaling up

### Storage: where your code lives locally

| Option | Best for | Free tier |
|--------|----------|-----------|
| **Google Drive** *(used)* | Auto-backup, access from anywhere, familiar UI | 15 GB free |
| **iCloud Drive** | Mac-only, tight OS integration | 5 GB free |
| **Dropbox** | Cross-platform, good selective sync | 2 GB free |
| **Local only** | Simplest, fastest | Free |

Google Drive works seamlessly with git and Vercel — the synced local path is just a regular folder. The only gotcha: very long path names (with spaces) need quoting in terminal commands.

### Other hosting options

| Option | Best for | Free tier | Cron support |
|--------|----------|-----------|--------------|
| **Vercel** *(used)* | Serverless functions, instant deploys | Yes | Yes (Pro for custom schedules) |
| **GitHub Actions** | Scheduled jobs, public repos | Yes (2,000 min/mo) | Full cron syntax, free |
| **Railway** | Always-on apps, simple deploys | $5 credit/mo | Yes, via cron jobs |
| **Render** | Web services + cron jobs | Yes (spins down on idle) | Yes (native cron jobs) |
| **Fly.io** | Containerised apps, global edge | Yes (3 shared VMs) | Yes, via `fly machines run` |
| **AWS Lambda** | Scale to millions of runs | Yes (1M req/mo free) | Yes, via EventBridge |
| **Local cron** | Simplest, no account needed | Free | Yes, if machine is always on |

**Recommendation for noobs:** GitHub Actions for scheduling (free, reliable, visible logs) + Vercel for the HTTP endpoint.

### Other email sending options

| Option | Free tier | Setup complexity | Notes |
|--------|-----------|-----------------|-------|
| **Resend** *(used)* | 100 emails/day | Low — one API key | Best DX, modern API |
| **SendGrid** | 100 emails/day | Low — one API key | Industry standard, more config |
| **Postmark** | 100 emails/mo (trial) | Low | Best deliverability, transactional focus |
| **Mailgun** | 100 emails/day (trial) | Medium | Requires domain verification |
| **Amazon SES** | 62,000 emails/mo (from EC2) | High | Cheapest at scale ($0.10/1K emails) |
| **Gmail SMTP** | Free | High — App Passwords often blocked | Works on personal accounts only |

**Recommendation:** Resend for low volume. Amazon SES if you're sending thousands.

### What if I need a database?

This app is stateless — it fetches fresh data every run and doesn't store anything. But if you wanted to extend it (e.g. track which articles you've already seen, store user preferences, log send history), here are the options:

| Option | Best for | Free tier | Notes |
|--------|----------|-----------|-------|
| **Vercel KV** (Redis) | Simple key-value, flags, deduplication | Yes | Built into Vercel, one line to connect |
| **Vercel Postgres** | Structured data, SQL queries | Yes | Neon-powered, works with any Python SQL lib |
| **Supabase** | Full Postgres + auth + realtime | Yes (generous) | Best free Postgres, great dashboard |
| **PlanetScale** | MySQL, branching like git | Yes | Great for schema changes |
| **SQLite** | Local dev, single-user apps | Free | Serverless environments can't persist files — not for Vercel |
| **MongoDB Atlas** | Flexible schema, JSON-like docs | Yes (512MB) | Good for storing raw feed articles |
| **Upstash Redis** | Rate limiting, caching, queues | Yes | Serverless-native, per-request pricing |

**Example use cases for this app:**
- *Deduplication:* store article URLs in Redis — skip ones already sent
- *Read tracking:* log which links were clicked (needs a redirect proxy)
- *User preferences:* let subscribers pick their sections — store in Postgres
- *Send history:* write a row per send to Postgres — useful for debugging

**Recommendation for noobs:** Start without a DB — you probably don't need one. If you do, Supabase Postgres is the easiest to get started with and has a great UI.

---

## Use this yourself

Anyone can fork this repo and have their own daily brief running in under 10 minutes.

**1. Fork & clone**
```bash
# Fork on GitHub, then:
git clone https://github.com/<your-username>/daily-brief-app
cd daily-brief-app
```

**2. Get a Resend API key**
- Sign up free at [resend.com](https://resend.com) (100 emails/day free)
- Dashboard → API Keys → Create key

**3. Run locally**
```bash
export EMAIL_TO='you@gmail.com'
export RESEND_API_KEY='re_xxxxxxxxxxxx'
python3 daily_brief_email.py
```
No `pip install` needed — stdlib only.

**4. Deploy to Vercel**
```bash
npm install -g vercel
vercel --yes
```
Then add `EMAIL_TO` and `RESEND_API_KEY` in the Vercel dashboard under Environment Variables and redeploy.

**5. Whitelist the sender in Gmail**
The first email will go to spam. Add `onboarding@resend.dev` to your Gmail contacts (e.g. as "Daily Brief") and future emails go straight to inbox.

**6. Customise**
- Change tickers: edit `STOCKS` in `daily_brief_email.py`
- Add/remove feeds: edit `NEWS_FEEDS`
- Change the design: edit `branding-guidelines.md`

---

## Key lessons

| Lesson | Detail |
|--------|--------|
| stdlib > dependencies | Zero pip installs = zero deployment headaches |
| RSS feeds break | Always have a scrape fallback; beehiiv RSS was malformed XML |
| Gmail is hard to automate | App Passwords blocked on many accounts; use a dedicated email API |
| Cloudflare blocks headless requests | Always include a `User-Agent` header on outbound HTTP calls |
| Vercel auto-detection is aggressive | `"framework": null` in `vercel.json` opts out of framework detection |
| Keep secrets out from day 1 | Retrofitting env vars after a public push is painful |
