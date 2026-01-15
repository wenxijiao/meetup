from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


ACTIVITY_UNDERCOVER = "undercover"
ACTIVITY_STORY_CHAIN = "story_chain"


@dataclass(frozen=True)
class ActivityMeta:
    id: str
    title: str
    description: str


# Activity registry: id -> meta + state factory
_META: Dict[str, ActivityMeta] = {}
_STATE_FACTORY: Dict[str, Callable[[List[str], random.Random], Dict]] = {}


def register_activity(meta: ActivityMeta, state_factory: Callable[[List[str], random.Random], Dict]) -> None:
    _META[meta.id] = meta
    _STATE_FACTORY[meta.id] = state_factory


def get_activity_meta(activity_id: str) -> Optional[dict]:
    m = _META.get(activity_id)
    if not m:
        return None
    return {"id": m.id, "title": m.title, "description": m.description}


def choose_random_activity_id(rng: random.Random, exclude: Optional[str] = None) -> str:
    ids = [aid for aid in _META.keys() if aid != exclude]
    if not ids:
        # fallback to any registered id
        ids = list(_META.keys())
    return rng.choice(ids) if ids else ACTIVITY_UNDERCOVER


def create_activity_state(activity_id: str, participant_ids: List[str], rng: random.Random) -> Dict:
    factory = _STATE_FACTORY.get(activity_id)
    if not factory:
        return {"assignments": {}}
    return factory(participant_ids, rng)


# Import built-in activities (side-effect: register)
from . import undercover as _undercover  # noqa: E402,F401
from . import story_chain as _story_chain  # noqa: E402,F401

