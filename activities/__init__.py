"""
Activities package.

Each activity (mini-game) lives in its own module and registers itself in the registry.
"""

from .registry import (  # noqa: F401
    ACTIVITY_UNDERCOVER,
    ACTIVITY_STORY_CHAIN,
    choose_random_activity_id,
    create_activity_state,
    get_activity_meta,
)

