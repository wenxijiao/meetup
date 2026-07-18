"""Application configuration loaded without committing secrets to Git."""

from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st


def _streamlit_section(name: str) -> dict[str, Any]:
    """Return one Streamlit secrets section, or an empty dict when absent."""
    try:
        return dict(st.secrets[name])
    except (FileNotFoundError, KeyError, TypeError, ValueError):
        return {}


def get_auth_secret(name: str) -> str | None:
    """Read an auth secret from an environment variable or Streamlit Secrets."""
    env_name = f"MEETUPOPS_{name.upper()}"
    value = os.getenv(env_name)
    if value:
        return value

    value = _streamlit_section("auth").get(name)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def get_firebase_service_account() -> dict[str, Any] | None:
    """Read Firebase service-account data from env or Streamlit Secrets."""
    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not raw_json:
        try:
            raw_json = str(st.secrets["FIREBASE_SERVICE_ACCOUNT_JSON"])
        except (FileNotFoundError, KeyError):
            raw_json = None

    if raw_json:
        data = json.loads(raw_json)
    else:
        data = _streamlit_section("firebase_service_account")

    if not data:
        return None

    # Also accept credentials pasted with escaped newlines.
    private_key = data.get("private_key")
    if isinstance(private_key, str):
        data["private_key"] = private_key.replace("\\n", "\n")
    return data
