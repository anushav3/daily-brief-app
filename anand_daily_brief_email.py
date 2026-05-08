#!/usr/bin/env python3
"""
Anand's Daily Brief — Email Sender
Fetches latest fintech/payments/banking/Zelle news and sends a formatted HTML email via Resend.

Setup:
  1. Sign up at https://resend.com and get an API key
  2. Verify your sender email at resend.com/settings/domains (or use a verified domain)
  3. Set environment variables:
     export ANAND_EMAIL_TO='anand@gmail.com'
     export ANAND_EMAIL_FROM='Daily Brief <you@yourdomain.com>'
     export ANAND_RESEND_API_KEY='re_xxxxxxxxxxxx'
  4. Run:
     python3 anand_daily_brief_email.py
"""

import json
import re
import os
import sys
import ssl
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# ──────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────
EMAIL_TO       = os.environ.get("ANAND_EMAIL_TO", "")
EMAIL_FROM     = os.environ.get("ANAND_EMAIL_FROM", "Daily Brief <onboarding@resend.dev>")
RESEND_API_KEY = os.environ.get("ANAND_RESEND_API_KEY", "")

NEWS_FEEDS = [
    ("💸 Zelle News",             "https://news.google.com/rss/search?q=zelle+payments+fintech&hl=en-US&gl=US&ceid=US:en",   3),
    ("🚨 Zelle: Fraud & Scams",   "https://news.google.com/rss/search?q=zelle+fraud+scam+victim&hl=en-US&gl=US&ceid=US:en", 3),
    ("💳 Payments News",          "https://www.pymnts.com/feed/",                                                             2),
    ("🏦 Banking & Fintech",      "https://www.finextra.com/rss/headlines.aspx",                                              2),
    ("🤖 AI in Finance",          "https://tearsheet.co/feed/",                                                               2),
    ("🚀 Fintech Startups",       "https://www.paymentsdive.com/feeds/news/",                                                 2),
    ("📊 This Week in Fintech",   "https://www.thisweekinfintech.com/archive",                                                3),
]

SECTION_COLORS = {
    "💸 Zelle News":            "#00c9a7",
    "🚨 Zelle: Fraud & Scams":  "#ff4757",
    "💳 Payments News":         "#4da6ff",
    "🏦 Banking & Fintech":     "#23d18b",
    "🤖 AI in Finance":         "#7b68ee",
    "🚀 Fintech Startups":      "#f5a623",
    "📊 This Week in Fintech":  "#ff9f43",
}


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
def fetch_url(url: str, timeout: int = 12) -> str | None:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DailyBrief/1.0)"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] fetch failed for {url}: {e}")
        return None


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;",  "&", text)
    text = re.sub(r"&lt;",   "<", text)
    text = re.sub(r"&gt;",   ">", text)
    text = re.sub(r"&quot;", '"', text)
    return re.sub(r"\s+", " ", text).strip()


# ──────────────────────────────────────────────
#  CUSTOM SCRAPERS
# ──────────────────────────────────────────────
def fetch_twif(limit: int = 3) -> list[dict]:
    """Scrape This Week in Fintech from thisweekinfintech.com/archive (Beehiiv SPA)."""
    html = fetch_url("https://www.thisweekinfintech.com/archive")
    if not html:
        return []
    try:
        ctx_match = re.search(r'window\.__remixContext\s*=\s*(\{.*?\})\s*;', html, re.DOTALL)
        if not ctx_match:
            return []
        data = json.loads(ctx_match.group(1))
        posts = (
            data["state"]["loaderData"]["routes/archive"]
            ["page"]["viewable_page_version"]["content"]
            ["content"][0]["content"][0]["attrs"]["data"]["posts"]
        )
        results = []
        for p in posts[:limit]:
            title = p.get("web_title", "").strip()
            slug  = p.get("slug", "")
            date  = p.get("override_scheduled_at", "")
            if not title or not slug:
                continue
            results.append({
                "title": title,
                "link":  f"https://www.thisweekinfintech.com/p/{slug}",
                "desc":  "",
                "date":  date,
            })
        return results
    except Exception as e:
        print(f"  [WARN] TWIF scrape failed: {e}")
        return []


# ──────────────────────────────────────────────
#  RSS PARSING
# ──────────────────────────────────────────────
def parse_rss(content: str | None, limit: int = 4) -> list[dict]:
    if not content:
        return []
    try:
        root = ET.fromstring(content)
        ns = {
            'rss':     'http://purl.org/rss/1.0/',
            'rdf':     'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'dc':      'http://purl.org/dc/elements/1.1/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
        }

        items = []
        item_elements = (
            root.findall(".//item")
            or root.findall(".//rss:item", ns)
            or root.findall(".//{http://purl.org/rss/1.0/}item")
        )

        for item in item_elements[:limit]:
            def safe_text(*paths):
                for path in paths:
                    try:
                        text = item.findtext(path)
                        if text and isinstance(text, str):
                            return text.strip()
                    except:
                        continue
                return ""

            title = safe_text("title", "rss:title", "{http://purl.org/rss/1.0/}title")
            if not title:
                continue

            link = safe_text("link", "rss:link", "{http://purl.org/rss/1.0/}link")
            desc = safe_text("description", "rss:description", "{http://purl.org/rss/1.0/}description", "content:encoded")
            desc = strip_html(desc)[:600] if desc else ""
            date = safe_text("pubDate", "rss:pubDate", "{http://purl.org/rss/1.0/}pubDate", "dc:date")

            items.append({"title": title, "link": link, "desc": desc, "date": date})
        return items
    except Exception as e:
        print(f"  [WARN] RSS parse error: {e}")
        return []


def relative_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        clean = re.sub(r"\s+[A-Z]{2,4}$", "", date_str.strip())
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
        ]
        pub = None
        for fmt in formats:
            try:
                pub = datetime.strptime(clean, fmt)
                break
            except ValueError:
                continue
        if pub is None:
            return ""
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        now  = datetime.now(timezone.utc)
        diff = now - pub
        h    = int(diff.total_seconds() // 3600)
        m    = int(diff.total_seconds() // 60)
        if m < 1:   return "just now"
        if m < 60:  return f"{m}m ago"
        if h < 24:  return f"{h}h ago"
        d = diff.days
        return "yesterday" if d == 1 else f"{d}d ago"
    except Exception:
        return ""


# ──────────────────────────────────────────────
#  EMAIL HTML GENERATION
# ──────────────────────────────────────────────

def load_branding_css() -> str:
    try:
        with open("branding-guidelines.md", "r", encoding="utf-8") as f:
            content = f.read()
        css_match = re.search(r'```css\s*(.*?)\s*```', content, re.DOTALL)
        if css_match:
            return css_match.group(1).strip()
        print("  [WARN] Could not extract CSS from branding-guidelines.md")
        return ""
    except Exception as e:
        print(f"  [WARN] Could not load branding CSS: {e}")
        return ""

_HTML_STYLE = load_branding_css()

def build_email_html(news_sections: list[tuple]) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")

    # 3-column layout:
    # Col 1: Zelle News (top) + Payments News (bottom)
    # Col 2: Banking & Fintech (top) + AI in Finance (bottom)
    # Col 3: Fintech Startups + This Week in Fintech + Zelle Fraud & Scams
    sections_dict = dict(news_sections)
    arranged_sections = [
        ("💸 Zelle News",           sections_dict.get("💸 Zelle News",           [])),
        ("🏦 Banking & Fintech",    sections_dict.get("🏦 Banking & Fintech",    [])),
        ("🚀 Fintech Startups",     sections_dict.get("🚀 Fintech Startups",     [])),
        ("💳 Payments News",        sections_dict.get("💳 Payments News",        [])),
        ("🤖 AI in Finance",        sections_dict.get("🤖 AI in Finance",        [])),
        ("📊 This Week in Fintech", sections_dict.get("📊 This Week in Fintech", [])),
        ("🚨 Zelle: Fraud & Scams", sections_dict.get("🚨 Zelle: Fraud & Scams", [])),
    ]

    def build_section_html(section_list):
        html = ""
        for section_name, items in section_list:
            clean_section_name = re.sub(r'^[^\w\s]+\s*', '', section_name).strip()
            color = SECTION_COLORS.get(section_name, "#4da6ff")
            html += f'<div class="news-section">'
            html += f'<h3 class="sec-label" style="border-left:3px solid {color};padding-left:8px">{clean_section_name}</h3>'
            if not items:
                html += '<div class="news-item"><span style="color:#666666">No articles available</span></div>'
            else:
                for item in items:
                    desc = item.get("desc", "").strip()
                    if desc:
                        sentences = re.split(r'(?<=[.!?])\s+', desc)
                        summary = " ".join(s.strip() for s in sentences[:3] if s.strip())
                        if len(summary) > 400:
                            summary = summary[:397] + "..."
                        elif summary and not summary.endswith(('.', '!', '?')):
                            summary += "."
                        first_sentence = summary
                    else:
                        first_sentence = ""

                    sub_html = f'<span class="news-desc">{first_sentence}</span>' if first_sentence else ""
                    html += f"""
                    <div class="news-item">
                      <h4 class="news-title"><a href="{item['link']}" target="_blank" rel="noopener">{item['title']}</a></h4>
                      {sub_html}
                    </div>"""
            html += '</div>'
        return html

    news_html = f"""
    <div class="news-container">
      <div class="news-column">{build_section_html([arranged_sections[0]])}{build_section_html([arranged_sections[3]])}</div>
      <div class="news-column">{build_section_html([arranged_sections[1]])}{build_section_html([arranged_sections[4]])}</div>
      <div class="news-column">{build_section_html([arranged_sections[2]])}{build_section_html([arranged_sections[5]])}{build_section_html([arranged_sections[6]])}</div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <meta name="description" content="Daily brief with fintech, payments, Zelle and banking news"/>
  <title>Anand's Daily Brief — {today}</title>
  <style>{_HTML_STYLE}</style>
</head>
<body>
<main class="wrap" role="main">

  <!-- Header -->
  <header class="hero">
    <h1 class="hero-title">Anand's Daily Brief</h1>
    <p class="hero-sub">{today} · FinTech · Payments · Zelle · Banking</p>
  </header>

  <!-- News Section -->
  <section class="card">
    {news_html}
  </section>

  <!-- Footer -->
  <footer class="footer" role="contentinfo">
    <p>
      Sources: <a href="https://news.google.com/search?q=zelle+payments" target="_blank" rel="noopener">Zelle News</a> ·
      <a href="https://www.pymnts.com" target="_blank" rel="noopener">PYMNTS</a> ·
      <a href="https://www.finextra.com" target="_blank" rel="noopener">Finextra</a> ·
      <a href="https://tearsheet.co" target="_blank" rel="noopener">Tearsheet</a> ·
      <a href="https://www.paymentsdive.com" target="_blank" rel="noopener">Payments Dive</a> ·
      <a href="https://thisweekinfintech.com" target="_blank" rel="noopener">This Week in Fintech</a> ·
      <a href="https://techcrunch.com/tag/fintech" target="_blank" rel="noopener">TechCrunch Fintech</a><br/>
      Anand's Daily Brief · Daily at 8 AM PST
    </p>
  </footer>

</main>
</body>
</html>"""


# ──────────────────────────────────────────────
#  SEND EMAIL (Resend API)
# ──────────────────────────────────────────────
BRIEF_URL = "https://daily-brief-app.vercel.app/anand"  # live URL after deploy


def send_email(subject: str, api_key: str) -> None:
    today = datetime.now().strftime("%A, %B %d")
    notification_html = f"""<!DOCTYPE html>
<html>
<body style="font-family:Georgia,serif;background:#fff;padding:40px 20px;max-width:480px;margin:0 auto;">
  <p style="font-size:13px;color:#999;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px">Your Daily Brief</p>
  <h1 style="font-size:22px;font-weight:bold;color:#111;margin:0 0 20px">{today}</h1>
  <p style="font-size:15px;color:#444;margin-bottom:28px">FinTech · Payments · Zelle · Banking — ready to read.</p>
  <a href="{BRIEF_URL}" style="display:inline-block;background:#111;color:#fff;text-decoration:none;padding:12px 28px;border-radius:4px;font-size:14px;letter-spacing:0.05em">Read Today's Brief →</a>
  <p style="margin-top:32px;font-size:11px;color:#bbb">{BRIEF_URL}</p>
</body>
</html>"""

    payload = json.dumps({
        "from":    EMAIL_FROM,
        "to":      [EMAIL_TO],
        "subject": subject,
        "html":    notification_html,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "User-Agent":    "Mozilla/5.0 (compatible; DailyBrief/1.0)",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        result = json.loads(resp.read().decode())
    print(f"✅  Email sent to {EMAIL_TO} (id: {result.get('id', '?')})")


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────
def fetch_brief_data() -> str:
    """Fetch all news and return rendered HTML — shared by main() and the preview endpoint."""
    news_sections = []
    for section_name, rss_url, limit in NEWS_FEEDS:
        if section_name == "📊 This Week in Fintech":
            items = fetch_twif(limit)
        else:
            content = fetch_url(rss_url)
            items = parse_rss(content, limit)
        news_sections.append((section_name, items))

    return build_email_html(news_sections)


def main() -> None:
    print(f"\n{'='*55}")
    print(f"  Anand's Daily Brief  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}\n")

    if not EMAIL_TO:
        print("❌  ANAND_EMAIL_TO is not set. Run:  export ANAND_EMAIL_TO='anand@gmail.com'")
        sys.exit(1)

    # News
    print("📰 Fetching news feeds…")
    news_sections = []
    for section_name, rss_url, limit in NEWS_FEEDS:
        print(f"   {section_name}…", end=" ", flush=True)
        if section_name == "📊 This Week in Fintech":
            items = fetch_twif(limit)
        else:
            content = fetch_url(rss_url)
            items = parse_rss(content, limit)
        print(f"{len(items)} articles")
        news_sections.append((section_name, items))

    # Send notification email
    print("\n✉️  Sending notification email…")
    today   = datetime.now().strftime("%B %d, %Y")
    subject = f"⚡ Anand's Daily Brief — {today}"

    api_key = RESEND_API_KEY
    if not api_key:
        print(f"\n⚠️  ANAND_RESEND_API_KEY not set.")
        print(f"   Brief available at: {BRIEF_URL}")
        print("\n   To enable email notifications:")
        print("   1. Sign up at https://resend.com and get an API key")
        print("   2. Run:  export ANAND_RESEND_API_KEY='re_xxxxxxxxxxxx'")
        print("   3. Re-run this script")
        return

    try:
        send_email(subject, api_key)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌  Resend API error {e.code}: {body}")
        sys.exit(1)
    except Exception as e:
        print(f"❌  Failed to send: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
