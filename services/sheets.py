from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import gspread
from gspread.exceptions import WorksheetNotFound

TEAM_HEADERS = [
    "Team ID", "Team Name", "Time Zone", "Status", "Discord Role ID",
    "Created At", "Created By",
]
PLAYER_HEADERS = [
    "Player ID", "Discord User ID", "Display Name", "Steam ID",
    "Status", "Created At",
]
ROSTER_HEADERS = [
    "Roster ID", "Team ID", "Player ID", "Status",
    "Joined At", "Removed At", "Added By",
]
REP_HEADERS = [
    "Assignment ID", "Team ID", "Player ID", "Status",
    "Added At", "Removed At", "Added By",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8].upper()}"


class SheetsRepository:
    def __init__(self, sheet_id: str, service_account_info: dict[str, Any]):
        client = gspread.service_account_from_dict(service_account_info)
        self.book = client.open_by_key(sheet_id)
        self.teams = self._worksheet("Teams", TEAM_HEADERS)
        self.players = self._worksheet("Players", PLAYER_HEADERS)
        self.rosters = self._worksheet("Team Rosters", ROSTER_HEADERS)
        self.reps = self._worksheet("Team Representatives", REP_HEADERS)

    def _worksheet(self, title: str, headers: list[str]):
        try:
            ws = self.book.worksheet(title)
        except WorksheetNotFound:
            ws = self.book.add_worksheet(
                title=title,
                rows=1000,
                cols=max(10, len(headers)),
            )

        first_row = ws.row_values(1)
        if not first_row:
            ws.append_row(headers, value_input_option="RAW")
            ws.freeze(rows=1)
        elif first_row != headers:
            raise RuntimeError(
                f"Worksheet '{title}' has unexpected headers. "
                f"Expected: {headers}; found: {first_row}"
            )
        return ws

    @staticmethod
    def _records(ws) -> list[dict[str, str]]:
        return ws.get_all_records(default_blank="")

    @staticmethod
    def _row_number(records: list[dict[str, str]], predicate) -> int | None:
        for index, record in enumerate(records, start=2):
            if predicate(record):
                return index
        return None

    def create_team(
        self,
        name: str,
        timezone_name: str,
        discord_role_id: int,
        created_by: int,
    ) -> dict[str, str]:
        if self.find_team_by_name(name):
            raise ValueError("A team with that name already exists.")

        team = {
            "Team ID": make_id("TEAM"),
            "Team Name": name.strip(),
            "Time Zone": timezone_name.strip(),
            "Status": "Active",
            "Discord Role ID": str(discord_role_id),
            "Created At": utc_now(),
            "Created By": str(created_by),
        }
        self.teams.append_row(list(team.values()), value_input_option="RAW")
        return team

    def find_team_by_name(self, name: str) -> dict[str, str] | None:
        normalized = name.strip().casefold()
        return next(
            (
                row for row in self._records(self.teams)
                if str(row["Team Name"]).strip().casefold() == normalized
            ),
            None,
        )

    def get_active_roster(self, team_id: str) -> list[dict[str, Any]]:
        roster_rows = [
            row for row in self._records(self.rosters)
            if row["Team ID"] == team_id and row["Status"] == "Active"
        ]
        players = {row["Player ID"]: row for row in self._records(self.players)}
        active_rep_ids = {
            row["Player ID"] for row in self._records(self.reps)
            if row["Team ID"] == team_id and row["Status"] == "Active"
        }

        result: list[dict[str, Any]] = []
        for roster in roster_rows:
            player = players.get(roster["Player ID"], {})
            result.append({
                **roster,
                "Discord User ID": str(player.get("Discord User ID", "")),
                "Display Name": str(player.get("Display Name", "Unknown")),
                "Steam ID": str(player.get("Steam ID", "")),
                "Is Representative": roster["Player ID"] in active_rep_ids,
            })
        return result

    def _find_or_create_player(
        self,
        discord_user_id: int,
        display_name: str,
        steam_id: str,
    ) -> dict[str, str]:
        existing = next(
            (
                row for row in self._records(self.players)
                if str(row["Discord User ID"]) == str(discord_user_id)
            ),
            None,
        )
        if existing:
            return existing

        player = {
            "Player ID": make_id("PLAYER"),
            "Discord User ID": str(discord_user_id),
            "Display Name": display_name.strip(),
            "Steam ID": steam_id.strip(),
            "Status": "Active",
            "Created At": utc_now(),
        }
        self.players.append_row(list(player.values()), value_input_option="RAW")
        return player

    def add_roster_member(
        self,
        team: dict[str, str],
        discord_user_id: int,
        display_name: str,
        steam_id: str,
        added_by: int,
    ) -> dict[str, str]:
        player = self._find_or_create_player(
            discord_user_id,
            display_name,
            steam_id,
        )

        active_assignments = [
            row for row in self._records(self.rosters)
            if row["Player ID"] == player["Player ID"]
            and row["Status"] == "Active"
        ]
        if active_assignments:
            assigned_team_id = active_assignments[0]["Team ID"]
            if assigned_team_id == team["Team ID"]:
                raise ValueError("That player is already active on this roster.")
            raise ValueError("That player is already active on another team.")

        roster = {
            "Roster ID": make_id("ROSTER"),
            "Team ID": team["Team ID"],
            "Player ID": player["Player ID"],
            "Status": "Active",
            "Joined At": utc_now(),
            "Removed At": "",
            "Added By": str(added_by),
        }
        self.rosters.append_row(list(roster.values()), value_input_option="RAW")
        return {**roster, **player}

    def remove_roster_member(
        self,
        team_id: str,
        discord_user_id: int,
    ) -> dict[str, str]:
        player = next(
            (
                row for row in self._records(self.players)
                if str(row["Discord User ID"]) == str(discord_user_id)
            ),
            None,
        )
        if not player:
            raise ValueError("That Discord user does not have a player record.")

        roster_records = self._records(self.rosters)
        roster_row = self._row_number(
            roster_records,
            lambda row: (
                row["Team ID"] == team_id
                and row["Player ID"] == player["Player ID"]
                and row["Status"] == "Active"
            ),
        )
        if not roster_row:
            raise ValueError("That player is not active on this roster.")

        now = utc_now()
        self.rosters.update_cell(
            roster_row,
            ROSTER_HEADERS.index("Status") + 1,
            "Removed",
        )
        self.rosters.update_cell(
            roster_row,
            ROSTER_HEADERS.index("Removed At") + 1,
            now,
        )
        self._deactivate_rep(team_id, player["Player ID"], now)
        return player

    def assign_representative(
        self,
        team_id: str,
        discord_user_id: int,
        added_by: int,
    ) -> dict[str, Any]:
        member = next(
            (
                row for row in self.get_active_roster(team_id)
                if str(row["Discord User ID"]) == str(discord_user_id)
            ),
            None,
        )
        if not member:
            raise ValueError(
                "A representative must first be active on the team roster."
            )
        if member["Is Representative"]:
            raise ValueError("That player is already a team representative.")

        assignment = {
            "Assignment ID": make_id("REP"),
            "Team ID": team_id,
            "Player ID": member["Player ID"],
            "Status": "Active",
            "Added At": utc_now(),
            "Removed At": "",
            "Added By": str(added_by),
        }
        self.reps.append_row(list(assignment.values()), value_input_option="RAW")
        return member

    def remove_representative(
        self,
        team_id: str,
        discord_user_id: int,
    ) -> dict[str, Any]:
        member = next(
            (
                row for row in self.get_active_roster(team_id)
                if str(row["Discord User ID"]) == str(discord_user_id)
            ),
            None,
        )
        if not member:
            raise ValueError("That player is not active on this team.")
        if not member["Is Representative"]:
            raise ValueError("That player is not an active representative.")

        self._deactivate_rep(team_id, member["Player ID"], utc_now())
        return member

    def _deactivate_rep(self, team_id: str, player_id: str, removed_at: str) -> None:
        records = self._records(self.reps)
        row_number = self._row_number(
            records,
            lambda row: (
                row["Team ID"] == team_id
                and row["Player ID"] == player_id
                and row["Status"] == "Active"
            ),
        )
        if row_number:
            self.reps.update_cell(
                row_number,
                REP_HEADERS.index("Status") + 1,
                "Removed",
            )
            self.reps.update_cell(
                row_number,
                REP_HEADERS.index("Removed At") + 1,
                removed_at,
            )
