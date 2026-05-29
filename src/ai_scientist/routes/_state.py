from __future__ import annotations

from ..config import settings


class _State:
    store = None
    orchestrator = None
    object_store = None
    clerk_verifier = None
    base_dir = None


state = _State()


def init_app(store, orchestrator, object_store, clerk_verifier, base_dir):
    state.store = store
    state.orchestrator = orchestrator
    state.object_store = object_store
    state.clerk_verifier = clerk_verifier
    state.base_dir = base_dir
