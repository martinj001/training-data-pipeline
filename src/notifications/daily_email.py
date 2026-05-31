"""
daily_email.py
Sends today's workout from the current training plan to your inbox.

Run manually to test:
    python src/notifications/daily_email.py

Scheduled automatically via Windows Task Scheduler at 6:30 AM —
see docs/setup-daily-email.md for setup instructions.
"""

import os
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

PLANS_DIR = PROJECT_ROOT / "data" / "plans"
GMAIL_USER = os.getenv("GMAIL_USER", "martinj001@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", GMAIL_USER)  # defaults to yourself


# ---------------------------------------------------------------------------
# Plan reading
# ---------------------------------------------------------------------------

def get_current_plan() -> str | None:
    """Return the content of the most recent plan file, or None."""
    if not PLANS_DIR.exists():
        return None
    plans = list(PLANS_DIR.glob("*.md"))
    if not plans:
        return None
    latest = max(plans, key=lambda f: f.stem)
    return latest.read_text(encoding="utf-8")


def extract_today_section(plan_text: str) -> str | None:
    """
    Find today's workout in the plan.

    Tries two approaches:
    1. Heading-based — looks for a ### heading containing today's date.
       Works if future plans are written with per-day headings.
    2. Table-based — looks for a table row containing today's date.
       Works for the current plan format:
         | May 27 | Wed | Cardio | Zwift — zone 2 aerobic ride | 45–60 min |
       For strength days it also fetches the full session detail section.
    """
    result = _extract_from_table(plan_text)
    if result:
        return result
    return _extract_by_heading(plan_text)


def _extract_by_heading(plan_text: str) -> str | None:
    """Look for a ### heading that contains today's date."""
    today = datetime.now()
    day = today.day

    patterns = [
        today.strftime(f"%A, %B {day}"),   # Wednesday, May 27
        today.strftime(f"%B {day}"),         # May 27
        today.strftime("%Y-%m-%d"),          # 2026-05-27
        today.strftime(f"%A {day}"),         # Wednesday 27
    ]

    lines = plan_text.splitlines()

    for pattern in patterns:
        for i, line in enumerate(lines):
            if re.search(re.escape(pattern), line, re.IGNORECASE):
                heading_match = re.match(r"^(#{1,6})\s", line)
                if not heading_match:
                    continue
                level = len(heading_match.group(1))
                section = [line]
                for j in range(i + 1, len(lines)):
                    next_heading = re.match(r"^(#{1,6})\s", lines[j])
                    if next_heading and len(next_heading.group(1)) <= level:
                        break
                    section.append(lines[j])
                if len(section) > 1:
                    return "\n".join(section).strip()

    return None


def _extract_from_table(plan_text: str) -> str | None:
    """
    Find today's row in a markdown schedule table.

    Expected columns: | Date | Day | Pillar | Session | Duration |
    e.g.  | May 27 | Wed | Cardio | Zwift — zone 2 aerobic ride | 45–60 min |

    For strength sessions it also appends the matching ### session section
    so the email contains the actual exercises, not just the session name.
    """
    today = datetime.now()
    day = today.day

    date_patterns = [
        today.strftime(f"%B {day}"),   # May 27
        today.strftime("%Y-%m-%d"),    # 2026-05-27
    ]

    for pattern in date_patterns:
        for line in plan_text.splitlines():
            # Must be a table row containing this date
            if "|" not in line:
                continue
            if not re.search(re.escape(pattern), line, re.IGNORECASE):
                continue

            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) < 3:
                continue

            # Columns: Date, Day, Pillar, Session, Duration
            date_col    = cols[0]                          # May 27
            day_col     = cols[1] if len(cols) > 1 else "" # Wed
            pillar      = cols[2] if len(cols) > 2 else "" # Cardio
            session     = cols[3] if len(cols) > 3 else "" # Zwift — zone 2 aerobic ride
            duration    = cols[4] if len(cols) > 4 else "" # 45–60 min

            # Build the header line
            day_full = today.strftime("%A")  # Wednesday
            lines = [
                f"### {day_full}, {date_col}",
                "",
                f"**{pillar}** — {session}  ",
            ]
            if duration:
                lines.append(f"⏱ {duration}")

            # For strength days, find and append the full session section
            if "strength" in pillar.lower() or "session" in session.lower():
                detail = _find_session_detail(plan_text, session)
                if detail:
                    lines += ["", "---", "", detail]

            return "\n".join(lines)

    return None


def _find_session_detail(plan_text: str, session_name: str) -> str | None:
    """
    Find the ### heading section that best matches session_name.

    e.g. "Session A — Upper / Push-Pull" → finds
         "### Session A — Upper / Push-Pull (~60 min)"
    """
    lines = plan_text.splitlines()

    # Try progressively shorter prefixes of session_name to find a match
    # e.g. first try full name, then just "Session A", then "Session"
    words = session_name.split()
    candidates = [
        " ".join(words[:k]) for k in range(len(words), 0, -1) if k >= 2
    ]

    for candidate in candidates:
        for i, line in enumerate(lines):
            if not re.match(r"^#{1,6}\s", line):
                continue
            if re.search(re.escape(candidate), line, re.IGNORECASE):
                # Grab content until the next same-or-higher heading
                level = len(re.match(r"^(#{1,6})\s", line).group(1))
                section = [line]
                for j in range(i + 1, len(lines)):
                    nxt = re.match(r"^(#{1,6})\s", lines[j])
                    if nxt and len(nxt.group(1)) <= level:
                        break
                    section.append(lines[j])
                if len(section) > 1:
                    return "\n".join(section).strip()

    return None


# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------

def _md_inline(text: str) -> str:
    """Convert inline markdown (**bold**, *italic*) to HTML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def plan_to_html(md: str) -> str:
    """Convert a subset of markdown to clean HTML for email."""
    lines = md.splitlines()
    html = []
    in_ul = False

    for line in lines:
        stripped = line.rstrip()

        if stripped.startswith("### "):
            if in_ul:
                html.append("</ul>")
                in_ul = False
            html.append(
                f"<h3 style='color:#2c3e50;margin:18px 0 6px'>"
                f"{_md_inline(stripped[4:])}</h3>"
            )
        elif stripped.startswith("## "):
            if in_ul:
                html.append("</ul>")
                in_ul = False
            html.append(
                f"<h2 style='color:#1a252f;border-bottom:1px solid #ddd;"
                f"padding-bottom:6px;margin-top:24px'>"
                f"{_md_inline(stripped[3:])}</h2>"
            )
        elif stripped.startswith("# "):
            if in_ul:
                html.append("</ul>")
                in_ul = False
            html.append(
                f"<h1 style='color:#1a252f'>{_md_inline(stripped[2:])}</h1>"
            )
        elif re.match(r"^[-*]\s", stripped):
            if not in_ul:
                html.append("<ul style='padding-left:20px;margin:6px 0'>")
                in_ul = True
            html.append(f"<li>{_md_inline(stripped[2:])}</li>")
        elif stripped == "":
            if in_ul:
                html.append("</ul>")
                in_ul = False
        else:
            if in_ul:
                html.append("</ul>")
                in_ul = False
            html.append(f"<p style='margin:6px 0'>{_md_inline(stripped)}</p>")

    if in_ul:
        html.append("</ul>")

    return "\n".join(html)


# ---------------------------------------------------------------------------
# Email assembly
# ---------------------------------------------------------------------------

def build_email(
    today_section: str | None,
    plan_text: str | None,
) -> tuple[str, str, str]:
    """
    Returns (subject, plain_text, html).
    """
    today = datetime.now()
    date_label = today.strftime(f"%A, %B {today.day}")  # Wednesday, May 27

    nudge = (
        "Open Claude and say:\n\n"
        "\"Time for a new training plan. Check my recent workouts and "
        "recovery and write the next block.\""
    )
    nudge_html = (
        "<p>Open Claude and say:</p>"
        "<blockquote style='border-left:3px solid #ccc;margin:12px 0;"
        "padding:8px 16px;color:#555;font-style:italic'>"
        "Time for a new training plan. Check my recent workouts and "
        "recovery and write the next block."
        "</blockquote>"
    )

    # --- subject ---
    if today_section:
        subject = f"Training — {date_label}"
    else:
        subject = f"Plan update needed — {date_label}"

    # --- plain text ---
    if today_section:
        plain = today_section
    else:
        plain = f"No entry found for {date_label} in your current plan.\n\n{nudge}"

    # --- HTML body content ---
    if today_section:
        body_html = plan_to_html(today_section)
    else:
        body_html = (
            f"<p>No entry found for <strong>{date_label}</strong> in your current plan.</p>"
            + nudge_html
        )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
    max-width: 600px; margin: 0 auto; padding: 20px; color: #2c3e50;
    font-size: 15px; line-height: 1.5;
  }}
  .header {{
    background: #2c3e50; color: white; padding: 16px 22px;
    border-radius: 8px 8px 0 0;
  }}
  .header h2 {{ margin: 0; font-size: 20px; }}
  .header p  {{ margin: 4px 0 0; font-size: 13px; opacity: 0.75; }}
  .body {{
    background: #fafafa; padding: 22px; border-radius: 0 0 8px 8px;
    border: 1px solid #e0e0e0; border-top: none;
  }}
  .footer {{
    margin-top: 20px; font-size: 11px; color: #bbb; text-align: center;
  }}
</style>
</head>
<body>
  <div class="header">
    <h2>🏋️ Today's Training</h2>
    <p>{date_label}</p>
  </div>
  <div class="body">
    {body_html}
  </div>
  <div class="footer">training-data-pipeline · sent at 6:30 AM</div>
</body>
</html>"""

    return subject, plain, html


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def send_email(subject: str, plain: str, html: str) -> None:
    if not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_APP_PASSWORD is not set in your .env file.\n"
            "See docs/setup-daily-email.md for instructions."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, EMAIL_TO, msg.as_string())

    safe_subject = subject.encode("ascii", errors="replace").decode("ascii")
    print(f"OK  Email sent to {EMAIL_TO}  [{safe_subject}]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

LOG_FILE = PROJECT_ROOT / "data" / "email_log.txt"


def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    try:
        log("Script started")
        log(f"PROJECT_ROOT = {PROJECT_ROOT}")
        log(f"GMAIL_USER = {GMAIL_USER}")
        log(f"EMAIL_TO = {EMAIL_TO}")
        log(f"GMAIL_APP_PASSWORD set = {bool(GMAIL_APP_PASSWORD)}")

        plan_text = get_current_plan()
        log(f"Plan found = {plan_text is not None}")

        today_section = extract_today_section(plan_text) if plan_text else None
        log(f"Today section found = {today_section is not None}")

        subject, plain, html = build_email(today_section, plan_text)
        safe_subject = subject.encode("ascii", errors="replace").decode("ascii")
        log(f"Subject = {safe_subject}")

        send_email(subject, plain, html)
        log("Email sent successfully")

    except Exception as e:
        log(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
