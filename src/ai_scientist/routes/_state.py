from __future__ import annotations

STORE = None
ORCHESTRATOR = None
OBJECT_STORE = None
CLERK_VERIFIER = None
BASE_DIR = None


def init_app(store, orchestrator, object_store, clerk_verifier, base_dir):
    global STORE, ORCHESTRATOR, OBJECT_STORE, CLERK_VERIFIER, BASE_DIR
    STORE = store
    ORCHESTRATOR = orchestrator
    OBJECT_STORE = object_store
    CLERK_VERIFIER = clerk_verifier
    BASE_DIR = base_dir
