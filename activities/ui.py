from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class ParticipantRenderer(Protocol):
    def render_participant(
        self,
        *,
        state: Dict[str, Any],
        participant_id: str,
        round_no: int,
        table_number: str,
        updated_by: str,
    ) -> None: ...


_PARTICIPANT_RENDERERS: Dict[str, ParticipantRenderer] = {}


def register_participant_renderer(activity_id: str, renderer: ParticipantRenderer) -> None:
    _PARTICIPANT_RENDERERS[activity_id] = renderer


def render_activity_participant(
    activity_id: str,
    *,
    state: Dict[str, Any],
    participant_id: str,
    round_no: int,
    table_number: str,
    updated_by: str,
) -> bool:
    """
    Returns True if a renderer exists and was called, else False.
    """
    renderer = _PARTICIPANT_RENDERERS.get(activity_id)
    if not renderer:
        return False
    renderer.render_participant(
        state=state,
        participant_id=participant_id,
        round_no=round_no,
        table_number=str(table_number),
        updated_by=updated_by,
    )
    return True

