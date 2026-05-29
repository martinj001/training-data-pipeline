# Daily Training Email — Setup Guide

Every morning at 6:30 AM, a Python script reads your current training plan,
finds today's entry, and emails it to you. No need to open VS Code.

---

## Step 1 — Create a Gmail App Password

Google won't let scripts log in with your regular password. Instead you
create a special one-time "App Password" that only this script uses.

1. Go to **https://myaccount.google.com/apppasswords**
   (you must have 2-Step Verification turned on — if not, Google will prompt you)
2. Under **"App name"**, type something like `training-pipeline`
3. Click **Create**
4. Google shows you a 16-character password like `abcd efgh ijkl mnop`
5. Copy it — you only see it once

---

## Step 2 — Add the password to your .env

Open `c:\Users\marti\dev\training-data-pipeline\.env` and add these lines
(they may already be there as placeholders):

```
GMAIL_USER=martinj001@gmail.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
EMAIL_TO=martinj001@gmail.com
```

Replace `abcdefghijklmnop` with your actual 16-character App Password
(no spaces needed).

---

## Step 3 — Test it manually

Open a terminal, navigate to the project folder, and run:

```powershell
cd C:\Users\marti\dev\training-data-pipeline
python src/notifications/daily_email.py
```

You should see:
```
OK  Email sent to martinj001@gmail.com  [Training — Wednesday, May 27]
```

Check your inbox. If something looks wrong, see the Troubleshooting section below.

---

## Step 4 — Find your Python path

Windows Task Scheduler runs in a stripped-down environment and can't find
`python` via the PATH. You need the full path to your Python executable.

Run this in any PowerShell window:

```powershell
(Get-Command python).Source
```

It should return something like:
```
C:\Users\marti\AppData\Local\Programs\Python\Python313\python.exe
```

---

## Step 5 — Schedule it with Windows Task Scheduler

Open PowerShell **as Administrator** (right-click → Run as administrator) and run,
substituting your Python path from Step 4:

```powershell
$action  = New-ScheduledTaskAction `
    -Execute "C:\Users\marti\AppData\Local\Programs\Python\Python313\python.exe" `
    -Argument "src\notifications\daily_email.py" `
    -WorkingDirectory "C:\Users\marti\dev\training-data-pipeline"

$trigger = New-ScheduledTaskTrigger -Daily -At "06:30"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName  "DailyTrainingEmail" `
    -Action    $action `
    -Trigger   $trigger `
    -Settings  $settings `
    -RunLevel  Highest `
    -Force
```

To verify it was created:
```powershell
Get-ScheduledTask -TaskName "DailyTrainingEmail"
```

To run it right now (test without waiting until 6:30):
```powershell
Start-ScheduledTask -TaskName "DailyTrainingEmail"
```

To remove it later:
```powershell
Unregister-ScheduledTask -TaskName "DailyTrainingEmail" -Confirm:$false
```

> **Note:** Using just `python` instead of the full path will cause the task to
> silently fail — Task Scheduler's PATH doesn't include your Python installation.

---

## How the script picks "today's workout"

The script reads the latest file in `data/plans/` and searches for today's date.
It handles two plan formats:

**Table format** (current plans written by Claude):
```
| May 27 | Wed | Cardio | Zwift — zone 2 aerobic ride | 45–60 min |
```

**Heading format** (alternative):
```
### Wednesday, May 27
```

For **strength days**, the full session detail (exercises, sets, reps) is automatically
included so you have everything you need without opening VS Code.

If today's date isn't in the plan (e.g. the plan has expired), you'll get a
**"Plan update needed"** email prompting you to ask Claude for a new block.
If there's no plan file at all, same nudge.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `GMAIL_APP_PASSWORD is not set` | Check your `.env` has the right key name |
| `SMTPAuthenticationError` | App Password is wrong — re-create one at myaccount.google.com/apppasswords |
| `No training plan found` | Ask Claude to write a plan; it uses `write_plan` to save it to `data/plans/` |
| Task runs but no email arrives | Use the full Python path (see Step 4) — `python` alone won't work in Task Scheduler |
| Task doesn't run at 6:30 | In Task Scheduler, check the task's **History** tab for errors; ensure the PC isn't asleep |
