from __future__ import annotations

import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _id_set(name: str) -> set[int]:
    raw = os.getenv(name, "")
    return {int(item.strip()) for item in raw.split(",") if item.strip()}


@dataclass(frozen=True)
class Settings:
    discord_token: str
    test_guild_id: int | None
    google_sheet_id: str
    service_account_info: dict
    admin_role_ids: set[int]
    league_official_role_ids: set[int]


def load_settings() -> Settings:
    test_guild_raw = os.getenv("TEST_GUILD_ID", "").strip()
    credentials_raw = _required("GOOGLE_SERVICE_ACCOUNT_JSON")

    try:
        credentials = json.loads(credentials_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON must contain the complete service-account JSON."
        ) from exc

    return Settings(
        discord_token=_required("DISCORD_TOKEN"),
        test_guild_id=int(test_guild_raw) if test_guild_raw else None,
        google_sheet_id=_required("GOOGLE_SHEET_ID"),
        service_account_info=credentials,
        admin_role_ids=_id_set("ADMIN_ROLE_IDS"),
        league_official_role_ids=_id_set("LEAGUE_OFFICIAL_ROLE_IDS"),
    )
