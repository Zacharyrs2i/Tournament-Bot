# HLL Tournament Bot — Team & Roster Test Build

This first build includes:

- Admin-only team creation
- Admin and League Official roster management
- Team representative assignment and removal
- Automatic Google Sheet tab/header creation
- Historical roster records instead of row deletion
- Automatic representative removal when a player leaves a roster

## Commands

| Command | Permission |
|---|---|
| `/team create` | Admin Team |
| `/team roster-add` | Admin Team or League Official |
| `/team roster-remove` | Admin Team or League Official |
| `/team rep-add` | Admin Team or League Official |
| `/team rep-remove` | Admin Team or League Official |
| `/team roster-view` | Everyone |

## Google Sheet setup

1. Create a blank Google Sheet.
2. Copy the spreadsheet ID from the URL between `/d/` and `/edit`.
3. Create a Google Cloud project.
4. Enable the Google Sheets API and Google Drive API.
5. Create a service account and download its JSON key.
6. Share the Google Sheet with the service account's `client_email` as an editor.
7. Store the spreadsheet ID and full service-account JSON in environment variables.

The bot creates these tabs automatically:

- `Teams`
- `Players`
- `Team Rosters`
- `Team Representatives`

Do not rename the generated headers.

## Environment variables

Copy `.env.example` to `.env` for local testing:

```env
DISCORD_TOKEN=your_bot_token
TEST_GUILD_ID=your_test_server_id
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
ADMIN_ROLE_IDS=111111111111111111
LEAGUE_OFFICIAL_ROLE_IDS=222222222222222222
```

Multiple role IDs may be comma-separated. Never commit `.env` or a service-account key file.

## Discord setup

1. Create a Discord application and bot.
2. Enable **Server Members Intent**.
3. Invite it with the `bot` and `applications.commands` scopes.
4. Give it View Channels, Send Messages, Embed Links, and Use Application Commands permissions.
5. Enable Discord Developer Mode and copy the required server and role IDs.

## Run in Codespaces or Linux

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

## Initial test order

1. `/team create`
2. `/team roster-add`
3. `/team roster-view`
4. `/team rep-add`
5. `/team roster-view`
6. `/team rep-remove`
7. `/team roster-remove`

Confirm that League Officials can manage existing teams but cannot create a new team.
