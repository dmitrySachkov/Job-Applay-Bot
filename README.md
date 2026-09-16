# job-apply-bot

A Claude Code project that turns a raw job posting into a tailored application:
gap analysis against your resume → adapted CV → humanized text → an Obsidian
note per application → a synced row in a Google Sheet for tracking.

Built as a set of [Claude Code](https://claude.com/claude-code) skills, so the
whole workflow runs as a normal conversation with Claude — no separate app,
no web UI.

## What it does

1. You paste a job posting into the chat.
2. **`vacancy-intake`** extracts the role, stack, seniority, location, salary,
   and flags obvious dealbreakers. Creates a draft note in the Obsidian vault.
3. **`cv-adapt`** compares the posting against your master resume
   (`templates/cv_master.docx`), writes a gap analysis (what's covered, what's
   partially covered, what's honestly missing), and drafts a tailored CV /
   cover letter.
4. **`humanize`** runs the draft through a checklist of AI-writing tells
   (uniform bullet rhythm, suspiciously round numbers, corporate filler
   phrases, absence of natural imperfection) and rewrites it so it reads like
   a person wrote it.
5. The final adapted CV is saved to `output/`, linked from the vault note.
6. **`status-sync`** keeps the Obsidian note and a Google Sheet row in sync
   whenever you update an application's status (applied, screening,
   interview, offer, rejected).

## Requirements

- [Claude Code](https://claude.com/claude-code)
- Python 3.10+
- A Google Cloud project with the Sheets and Drive APIs enabled, and a
  service account with edit access to a Google Sheet (see setup below)
- Obsidian (optional but recommended) to browse the `vault/` folder

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/job-apply-bot.git
cd job-apply-bot
./scripts/setup.sh
```

The setup script will:
- ask for the path to your `service-account.json`
- ask for your Google Sheet ID and tab name
- create `.env`
- create a virtualenv and install dependencies
- run a test write to confirm the Sheet integration works

Then drop your resume at `templates/cv_master.docx`, open `vault/` as an
Obsidian vault, and start Claude Code in the project directory:

```bash
claude
```

## Manual setup (Google Sheet)

If you'd rather not use `setup.sh`, or it fails and you want to debug by
hand:

1. Go to the [Google Cloud Console](https://console.cloud.google.com),
   create or select a project.
2. **APIs & Services → Library** → enable **Google Sheets API** and
   **Google Drive API**.
3. **APIs & Services → Credentials → Create Credentials → Service Account**.
   Name it whatever you like; you can skip granting it a project-level role.
4. Open the new service account → **Keys → Add Key → Create new key → JSON**.
   Save the downloaded file as `service-account.json` in the project root.
5. Create a Google Sheet (empty is fine — the script creates headers on
   first run). Copy its ID from the URL, the part between `/d/` and `/edit`.
6. Open the sheet's client email from step 4's JSON (`client_email` field),
   share the sheet with it, grant **Editor** access.
7. Copy `.env.example` to `.env` and fill in `GOOGLE_SHEETS_CREDS` (absolute
   path to `service-account.json`) and `GOOGLE_SHEET_ID`.
8. Install dependencies and test:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python scripts/sheets_sync.py --company "Test" --role "Test" --status draft
   ```

## Project structure

```
job-apply-bot/
  CLAUDE.md                     # project-level rules Claude Code reads automatically
  .claude/skills/
    vacancy-intake/SKILL.md
    cv-adapt/SKILL.md
    humanize/SKILL.md
    status-sync/SKILL.md
  vault/applications/*.md       # one Obsidian note per application
  templates/cv_master.docx      # your master resume — never overwritten
  output/CV_*.docx              # tailored CVs, one per application
  scripts/
    setup.sh                    # interactive first-time setup
    sheets_sync.py               # Google Sheet sync
  requirements.txt
  .env.example
```

## Notes on the design

- **`templates/cv_master.docx` is read-only by convention.** Every tailored
  version is a new file in `output/`, named after the company and role.
- **The vault note and the Sheet row are always updated together**, via
  `status-sync`, so they never drift out of sync.
- **`humanize` is mandatory** before anything gets saved to `output/`. AI
  text detectors on resumes are unreliable and produce false positives
  fairly often, especially for non-native English writers — the goal here
  isn't to fool a detector, it's to make the text read naturally to a human
  recruiter.
- The project is intentionally independent of any other automation you might
  run alongside it (e.g. a separate scraping/scoring pipeline for finding
  vacancies). This repo only handles what happens *after* you've decided a
  posting is worth applying to.

## Privacy

`.gitignore` excludes `.env`, `service-account.json`, your resume
(`templates/cv_master.docx`), adapted CVs (`output/*.docx`), and your actual
application notes (`vault/applications/*.md`) — so cloning or forking this
repo gives you the tooling, not anyone's personal job-search data.

## License

MIT — see [LICENSE](LICENSE).
