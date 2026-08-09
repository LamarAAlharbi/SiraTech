"""
Business rules for SiraTech gamification: XP amounts, badge thresholds, and
discovery bookkeeping.

This module owns all game-design logic. The storage layer
(`gamification_repository.py`) is a plain, opinion-free data store, so XP
values and badge thresholds can be tuned here without ever touching SQL —
and the whole storage layer can be swapped for a production database later
without changing anything in here.

Discovery types recognized by the API:
  - "landmark"          — visited/opened a known SiraTech landmark
  - "hidden_gem"         — identified an unlisted site via the Hidden Gems
                            (vision) feature
  - "historical_image"   — viewed a curated "See the Past" photo
  - "story"               — listened to a narrated guide story (TTS)
"""

from flask import current_app

from app.errors import ValidationError
from app.services import gamification_repository
from app.services.history_service import get_history_image_by_id
from app.services.landmarks_service import get_landmark_by_id

DISCOVERY_LANDMARK = "landmark"
DISCOVERY_HIDDEN_GEM = "hidden_gem"
DISCOVERY_HISTORICAL_IMAGE = "historical_image"
DISCOVERY_STORY = "story"

DISCOVERY_TYPES = (
    DISCOVERY_LANDMARK,
    DISCOVERY_HIDDEN_GEM,
    DISCOVERY_HISTORICAL_IMAGE,
    DISCOVERY_STORY,
)

# XP awarded per *new* discovery of each type. Hidden gems pay the most —
# they require successfully using the AI vision-recognition feature rather
# than opening an item from a known list.
XP_VALUES = {
    DISCOVERY_LANDMARK: 10,
    DISCOVERY_HISTORICAL_IMAGE: 15,
    DISCOVERY_STORY: 15,
    DISCOVERY_HIDDEN_GEM: 25,
}

# How many distinct landmark discoveries / distinct SiraTech locations are
# needed to unlock each badge. Tunable in one place.
HERITAGE_EXPLORER_LANDMARK_THRESHOLD = 3
HIDDEN_GEM_HUNTER_THRESHOLD = 3
TIME_TRAVELER_THRESHOLD = 3
STORY_LISTENER_THRESHOLD = 3
SAUDI_HERITAGE_EXPLORER_LOCATION_THRESHOLD = 4


def _heritage_explorer(counts, distinct_locations):
    return counts[DISCOVERY_LANDMARK] >= HERITAGE_EXPLORER_LANDMARK_THRESHOLD


def _hidden_gem_hunter(counts, distinct_locations):
    return counts[DISCOVERY_HIDDEN_GEM] >= HIDDEN_GEM_HUNTER_THRESHOLD


def _time_traveler(counts, distinct_locations):
    return counts[DISCOVERY_HISTORICAL_IMAGE] >= TIME_TRAVELER_THRESHOLD


def _story_listener(counts, distinct_locations):
    return counts[DISCOVERY_STORY] >= STORY_LISTENER_THRESHOLD


def _saudi_heritage_explorer(counts, distinct_locations):
    return len(distinct_locations) >= SAUDI_HERITAGE_EXPLORER_LOCATION_THRESHOLD


# Badge catalog: code -> display name, description, and the rule that
# decides whether a user has earned it. `check(counts, distinct_locations)`
# is called with the user's *current* per-type discovery counts and the
# set of distinct location_ids they've discovered a landmark in.
BADGES = {
    "heritage_explorer": {
        "name": "Heritage Explorer",
        "description": f"Discovered {HERITAGE_EXPLORER_LANDMARK_THRESHOLD} landmarks.",
        "check": _heritage_explorer,
    },
    "hidden_gem_hunter": {
        "name": "Hidden Gem Hunter",
        "description": f"Identified {HIDDEN_GEM_HUNTER_THRESHOLD} hidden gems with the vision feature.",
        "check": _hidden_gem_hunter,
    },
    "time_traveler": {
        "name": "Time Traveler",
        "description": f'Viewed {TIME_TRAVELER_THRESHOLD} historical "See the Past" images.',
        "check": _time_traveler,
    },
    "story_listener": {
        "name": "Story Listener",
        "description": f"Listened to {STORY_LISTENER_THRESHOLD} narrated stories.",
        "check": _story_listener,
    },
    "saudi_heritage_explorer": {
        "name": "Saudi Heritage Explorer",
        "description": (
            f"Discovered landmarks across {SAUDI_HERITAGE_EXPLORER_LOCATION_THRESHOLD}+ "
            "different SiraTech locations."
        ),
        "check": _saudi_heritage_explorer,
    },
}


def _repository():
    db_path = current_app.config["GAMIFICATION_DB_PATH"]
    return gamification_repository.get_repository(db_path)


def _resolve_location_id(discovery_type, item_id, provided_location_id):
    """
    Fill in location_id for discovery types backed by seed data, so the
    Saudi Heritage Explorer badge (distinct locations) works even when the
    client doesn't pass location_id itself. Raises NotFoundError (from the
    underlying service) if item_id doesn't refer to a real record.

    hidden_gem / story discoveries aren't necessarily tied to a known
    landmark (a hidden gem may not be in the seed data at all), so those
    trust the client-supplied location_id, if any, and fall back to None —
    it just won't count toward Saudi Heritage Explorer.
    """
    if discovery_type == DISCOVERY_LANDMARK:
        landmark = get_landmark_by_id(item_id)
        return landmark["location_id"]

    if discovery_type == DISCOVERY_HISTORICAL_IMAGE:
        image = get_history_image_by_id(item_id)
        landmark = get_landmark_by_id(image["landmark_id"])
        return landmark["location_id"]

    return provided_location_id


def _counts_for(repo, user_id):
    return {dtype: repo.count_by_type(user_id, dtype) for dtype in DISCOVERY_TYPES}


def _evaluate_new_badges(repo, user_id):
    """Check every badge rule against current totals and unlock any newly-earned ones."""
    counts = _counts_for(repo, user_id)
    distinct_locations = repo.distinct_locations(user_id, discovery_type=DISCOVERY_LANDMARK)
    already_unlocked = repo.unlocked_badge_codes(user_id)

    newly_unlocked = []
    for code, badge in BADGES.items():
        if code in already_unlocked:
            continue
        if badge["check"](counts, distinct_locations):
            if repo.unlock_badge(user_id, code):
                newly_unlocked.append(
                    {"code": code, "name": badge["name"], "description": badge["description"]}
                )
    return newly_unlocked


def record_discovery(user_id, discovery_type, item_id, location_id=None):
    """
    Record a discovery for a user: award XP if it's genuinely new, and
    unlock any badges the updated totals now qualify for.

    Never rewards the same (user_id, discovery_type, item_id) discovery
    twice — a repeat call returns already_discovered=True, xp_awarded=0,
    and no newly unlocked badges.
    """
    if discovery_type not in DISCOVERY_TYPES:
        raise ValidationError(
            f"'type' must be one of: {', '.join(DISCOVERY_TYPES)}.",
            details={"param": "type", "received": discovery_type, "allowed": list(DISCOVERY_TYPES)},
        )

    resolved_location_id = _resolve_location_id(discovery_type, item_id, location_id)

    repo = _repository()
    xp_value = XP_VALUES[discovery_type]
    is_new = repo.record_discovery(user_id, discovery_type, item_id, resolved_location_id, xp_value)

    newly_unlocked_badges = _evaluate_new_badges(repo, user_id) if is_new else []

    return {
        "already_discovered": not is_new,
        "xp_awarded": xp_value if is_new else 0,
        "newly_unlocked_badges": newly_unlocked_badges,
        "profile": get_profile(user_id),
    }


def get_profile(user_id):
    """Return a full gamification profile for a user (all zeros if they're new)."""
    repo = _repository()
    counts = _counts_for(repo, user_id)
    distinct_locations = repo.distinct_locations(user_id, discovery_type=DISCOVERY_LANDMARK)
    unlocked_codes = repo.unlocked_badge_codes(user_id)

    badges = [
        {"code": code, "name": badge["name"], "description": badge["description"]}
        for code, badge in BADGES.items()
        if code in unlocked_codes
    ]

    return {
        "user_id": user_id,
        "total_xp": repo.total_xp(user_id),
        "discovered_landmarks": {
            "count": counts[DISCOVERY_LANDMARK],
            "item_ids": [d["item_id"] for d in repo.list_discoveries(user_id, DISCOVERY_LANDMARK)],
        },
        "hidden_gems": {
            "count": counts[DISCOVERY_HIDDEN_GEM],
            "item_ids": [d["item_id"] for d in repo.list_discoveries(user_id, DISCOVERY_HIDDEN_GEM)],
        },
        "historical_images_viewed": {
            "count": counts[DISCOVERY_HISTORICAL_IMAGE],
            "item_ids": [
                d["item_id"] for d in repo.list_discoveries(user_id, DISCOVERY_HISTORICAL_IMAGE)
            ],
        },
        "stories_listened": {
            "count": counts[DISCOVERY_STORY],
            "item_ids": [d["item_id"] for d in repo.list_discoveries(user_id, DISCOVERY_STORY)],
        },
        "distinct_locations_explored": sorted(distinct_locations),
        "badges": badges,
    }
