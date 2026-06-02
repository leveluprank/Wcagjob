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

SEARCH_QUERIES = [
    "website accessibility assistant jobs",
    "web accessibility specialist remote",
    "accessibility consultant startup jobs",
]

STARTUP_JOB_BOARDS = [
    {
        "name": "Y Combinator (WorkAtAStartup)",
        "url": "https://www.workatastartup.com/jobs?q=accessibility",
    },
    {
        "name": "Wellfound (AngelList)",
        "url": "https://wellfound.com/jobs?q=accessibility+assistant",
    },
    {
        "name": "RemoteOK",
        "url": "https://remoteok.com/remote-accessibility-jobs",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def search_google_jobs(query):
    results = []
    try:
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}+jobs&num=5"
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for g in soup.find_all("div", class_="g")[:5]:
            title_tag = g.find("h3")
            link_tag = g.find("a")
            snippet_tag = g.find("div", class_="VwiC3b")
            if title_tag and link_tag:
                results.append({
                    "title": title_tag.get_text(),
                    "link": link_tag.get("href", ""),
                    "snippet": snippet_tag.get_text() if snippet_tag else "",
                    "source": "Google Search"
                })
    except Exception as e:
        print(f"Google search error: {e}")
    return results


def scrape_startup_boards():
    results = []
    for board in STARTUP_JOB_BOARDS:
        try:
            response = requests.get(board["url"], headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Sirf meaningful job titles lo
            job_links = soup.find_all("a", href=True)
            for link in job_links:
                text = link.get_text(strip=True)
                
                # Filters — garbage hatao
                if len(text) < 5 or len(text) > 100:
                    continue
                if any(skip in text.lower() for skip in [
                    "log in", "sign up", "remote ok", "join", "dark mode",
                    "hire", "post a job", "premium", "feed", "rss", "json",
                    "changelog", "faq", "help", "merch", "nomad", "web3",
                    "finance", "manager", "marketing", "support", "menu"
                ]):
                    continue
                if any(word in text.lower() for word in [
                    "accessibility", "a11y", "web", "assistant", "ux", "frontend"
                ]):
                    results.append({
                        "title": text,
                        "link": link["href"] if link["href"].startswith("http") else board["url"],
                        "snippet": f"Found on {board['name']}",
                        "source": board["name"]
                    })
        except Exception as e:
            print(f"Error scraping {board['name']}: {e}")
    return results


def build_email_html(all_jobs, date_str):
    job_rows = ""
    for job in all_jobs:
        link = job.get("link", "#")
        if not link.startswith("http"):
            link = "https://google.com/search?q=" + job["title"].replace(" ", "+")
        job_rows += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #eee;">
            <a href="{link}" style="font-weight:600;color:#1a1a2e;text-decoration:none;font-size:15px;">{job['title']}</a>
            <div style="color:#666;font-size:13px;margin-top:4px;">{job.get('snippet','')[:120]}</div>
            <span style="display:inline-block;margin-top:6px;background:#f0f4ff;color:#4361ee;font-size:11px;padding:2px 8px;border-radius:20px;">{job['source']}</span>
          </td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#f5f7ff;margin:0;padding:20px;">
    <div style="max-width:640px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
      <div style="background:linear-gradient(135deg,#4361ee,#3a0ca3);padding:28px 32px;">
        <h1 style="color:#fff;margin:0;font-size:22px;">Daily Job Search Results</h1>
        <p style="color:rgba(255,255,255,0.8);margin:8px 0 0;font-size:14px;">{date_str} — Website Accessibility Assistant Jobs</p>
      </div>
      <div style="padding:24px;">
        <p style="color:#444;margin:0 0 16px;">Found <strong>{len(all_jobs)} jobs</strong> across top startup boards and Google.</p>
        <table style="width:100%;border-collapse:collapse;border:1px solid #eee;border-radius:8px;overflow:hidden;">
          {job_rows if job_rows else '<tr><td style="padding:20px;text-align:center;color:#888;">No new jobs found today.</td></tr>'}
        </table>
        <p style="color:#aaa;font-size:12px;margin-top:24px;text-align:center;">Automated daily job search via GitHub Actions</p>
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
    print("Email sent!")


def main():
    print("Starting job search...")
    all_jobs = []
    for query in SEARCH_QUERIES:
        print(f"Searching: {query}")
        all_jobs.extend(search_google_jobs(query))
    print("Scraping startup boards...")
    all_jobs.extend(scrape_startup_boards())
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = job["title"][:40]
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    date_str = datetime.now().strftime("%B %d, %Y")
    print(f"Total jobs: {len(unique_jobs)}")
    html = build_email_html(unique_jobs, date_str)
    subject = f"🔍 {len(unique_jobs)} Accessibility Jobs Found — {date_str}"
    send_email(subject, html)

if __name__ == "__main__":
    main()