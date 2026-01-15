"""
Backward-compatible re-exports.

New activity system lives in `activities/` package.
Keep this module so older imports (data.activities) still work.
"""

from activities.registry import (  # noqa: F401
    ACTIVITY_UNDERCOVER,
    choose_random_activity_id,
    create_activity_state,
    get_activity_meta,
)

