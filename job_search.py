import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from datetime import datetime

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL = os.environ["TO_EMAIL"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

GOOGLE_QUERIES = [
    "website accessibility assistant jobs paid",
    "web accessibility specialist remote paid",
    "accessibility consultant paid internship",
    "WCAG accessibility analyst jobs",
    "digital accessibility engineer remote jobs",
]

JOB_BOARDS = [
    {"name": "RemoteOK", "url": "https://remoteok.com/remote-accessibility-jobs"},
    {"name": "Wellfound", "url": "https://wellfound.com/jobs?q=accessibility+assistant"},
    {"name": "WorkAtAStartup (YC)", "url": "https://www.workatastartup.com/jobs?q=accessibility"},
    {"name": "Glassdoor", "url": "https://www.glassdoor.com/Job/accessibility-assistant-jobs-SRCH_KO0,23.htm"},
    {"name": "Indeed", "url": "https://www.indeed.com/jobs?q=web+accessibility+assistant&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11"},
    {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs/search/?keywords=web+accessibility+assistant&f_WT=2"},
    {"name": "We Work Remotely", "url": "https://weworkremotely.com/remote-jobs/search?term=accessibility"},
]

GARBAGE_WORDS = [
    "log in", "sign up", "join", "dark mode", "hire", "post a job", "premium",
    "feed", "rss", "json", "changelog", "faq", "help", "merch", "nomad",
    "web3", "menu", "cookie", "privacy", "terms", "copyright", "follow us",
    "newsletter", "about us", "contact", "blog", "pricing", "home", "search",
    "filter", "sort", "salary", "company", "location", "all jobs", "browse",
    "create alert", "sign in", "register", "download", "upload"
]

UNPAID_WORDS = [
    "unpaid", "volunteer", "no compensation", "academic credit only",
    "for experience", "no pay", "free internship"
]

JOB_KEYWORDS = [
    "accessibility", "a11y", "wcag", "aria", "screen reader",
    "assistive technology", "web assistant", "ux accessibility",
    "digital accessibility", "inclusive design"
]


def is_paid(text):
    text_lower = text.lower()
    for word in UNPAID_WORDS:
        if word in text_lower:
            return False
    return True


def is_relevant(text):
    text_lower = text.lower()
    return any(word in text_lower for word in JOB_KEYWORDS)


def is_garbage(text):
    text_lower = text.lower()
    return any(skip in text_lower for skip in GARBAGE_WORDS)


def search_google_jobs(query):
    results = []
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}+remote&num=8"
        response = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(response.text, "html.parser")
        for g in soup.find_all("div", class_="g")[:8]:
            title_tag = g.find("h3")
            link_tag = g.find("a")
            snippet_tag = g.find("div", class_="VwiC3b")
            if title_tag and link_tag:
                title = title_tag.get_text()
                snippet = snippet_tag.get_text() if snippet_tag else ""
                if is_paid(title + " " + snippet):
                    results.append({
                        "title": title,
                        "link": link_tag.get("href", ""),
                        "snippet": snippet,
                        "source": "Google Search",
                        "type": "Paid Internship" if "intern" in title.lower() else "Full-time"
                    })
    except Exception as e:
        print(f"Google error: {e}")
    return results


def scrape_job_boards():
    results = []
    for board in JOB_BOARDS:
        try:
            response = requests.get(board["url"], headers=HEADERS, timeout=12)
            soup = BeautifulSoup(response.text, "html.parser")
            job_links = soup.find_all("a", href=True)
            for link in job_links:
                text = link.get_text(strip=True)
                if len(text) < 8 or len(text) > 120:
                    continue
                if is_garbage(text):
                    continue
                if not is_relevant(text):
                    continue
                if not is_paid(text):
                    continue
                href = link["href"]
                if not href.startswith("http"):
                    href = board["url"]
                results.append({
                    "title": text,
                    "link": href,
                    "snippet": f"Found on {board['name']}",
                    "source": board["name"],
                    "type": "Paid Internship" if "intern" in text.lower() else "Full-time"
                })
        except Exception as e:
            print(f"Error scraping {board['name']}: {e}")
    return results


def build_email_html(all_jobs, date_str):
    fulltime = [j for j in all_jobs if j["type"] == "Full-time"]
    internships = [j for j in all_jobs if j["type"] == "Paid Internship"]

    def make_rows(jobs):
        rows = ""
        for job in jobs:
            link = job.get("link", "#")
            if not link.startswith("http"):
                link = "https://google.com/search?q=" + job["title"].replace(" ", "+")
            badge_color = "#0d6e3f" if job["type"] == "Paid Internship" else "#4361ee"
            badge_bg = "#e6f4ee" if job["type"] == "Paid Internship" else "#f0f4ff"
            rows += f"""
            <tr>
              <td style="padding:14px 18px;border-bottom:1px solid #f0f0f0;">
                <a href="{link}" style="font-weight:600;color:#1a1a2e;text-decoration:none;font-size:15px;line-height:1.4;">{job['title']}</a>
                <div style="color:#666;font-size:13px;margin-top:5px;line-height:1.5;">{job.get('snippet','')[:130]}</div>
                <div style="margin-top:7px;display:flex;gap:6px;flex-wrap:wrap;">
                  <span style="background:{badge_bg};color:{badge_color};font-size:11px;padding:2px 10px;border-radius:20px;font-weight:600;">{job['type']}</span>
                  <span style="background:#f5f5f5;color:#666;font-size:11px;padding:2px 10px;border-radius:20px;">{job['source']}</span>
                </div>
              </td>
            </tr>"""
        return rows

    def section(title, icon, jobs, color):
        if not jobs:
            return ""
        return f"""
        <div style="margin-bottom:28px;">
          <h2 style="font-size:16px;color:{color};margin:0 0 12px;padding-bottom:8px;border-bottom:2px solid {color};">{icon} {title} ({len(jobs)})</h2>
          <table style="width:100%;border-collapse:collapse;border:1px solid #eee;border-radius:8px;overflow:hidden;">
            {make_rows(jobs)}
          </table>
        </div>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#f5f7ff;margin:0;padding:20px;">
    <div style="max-width:660px;margin:auto;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.09);">
      <div style="background:linear-gradient(135deg,#4361ee,#3a0ca3);padding:30px 32px;">
        <h1 style="color:#fff;margin:0;font-size:22px;">Daily Accessibility Job Search</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;">{date_str} — Paid Jobs & Paid Internships Only</p>
      </div>
      <div style="padding:28px;">
        <p style="color:#444;margin:0 0 20px;font-size:15px;">
          Found <strong>{len(all_jobs)} paid opportunities</strong> across LinkedIn, Glassdoor, Indeed, RemoteOK, Wellfound & more.
        </p>
        {section("Full-time Jobs", "💼", fulltime, "#4361ee")}
        {section("Paid Internships", "🌱", internships, "#0d6e3f")}
        {"<p style='text-align:center;color:#aaa;padding:20px;'>No paid jobs found today. Try again tomorrow.</p>" if not all_jobs else ""}
        <p style="color:#bbb;font-size:11px;margin-top:20px;text-align:center;border-top:1px solid #f0f0f0;padding-top:16px;">
          Automated daily search via GitHub Actions • Unpaid internships excluded
        </p>
      </div>
    </div>
    </body></html>
    """


def send_email(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, TO_EMAIL, msg.as_string())
    print("Email sent successfully!")


def main():
    print("Starting job search...")
    all_jobs = []

    for query in GOOGLE_QUERIES:
        print(f"Searching Google: {query}")
        all_jobs.extend(search_google_jobs(query))

    print("Scraping job boards...")
    all_jobs.extend(scrape_job_boards())

    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = job["title"][:40].lower()
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    date_str = datetime.now().strftime("%B %d, %Y")
    print(f"Total unique paid jobs: {len(unique_jobs)}")

    html = build_email_html(unique_jobs, date_str)
    subject = f"💼 {len(unique_jobs)} Paid Accessibility Jobs — {date_str}"
    send_email(subject, html)


if __name__ == "__main__":
    main()
