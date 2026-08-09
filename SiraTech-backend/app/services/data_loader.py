"""
Loads the seed JSON files into memory once per process.

This stands in for a real database in the prototype. Swapping this out
later for e.g. Postgres only means rewriting this module — the services
built on top of it (locations_service, landmarks_service, ...) don't
need to change their public functions.
"""

import json
import os
import threading

from flask import current_app

_cache = {}
_lock = threading.Lock()


def _data_dir():
    return current_app.config["DATA_DIR"]


def _load_json_file(filename):
    path = os.path.join(_data_dir(), filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Seed data file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load(filename):
    """Load a JSON seed file, caching by (data_dir, filename) for the process lifetime."""
    cache_key = (_data_dir(), filename)
    if cache_key in _cache:
        return _cache[cache_key]

    with _lock:
        if cache_key not in _cache:
            _cache[cache_key] = _load_json_file(filename)
    return _cache[cache_key]


def clear_cache():
    """Useful in tests when swapping DATA_DIR between cases."""
    with _lock:
        _cache.clear()
