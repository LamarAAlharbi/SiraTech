"""
The "Guide" service is the core of SiraTech: it answers
"tell me about this place" style questions by combining locations,
landmarks, and image metadata into a single response. It does NOT
plan itineraries, prices, or bookings — only informational lookups.
"""

from app.services import data_loader
from app.services.locations_service import get_location_by_id
from app.services.landmarks_service import get_landmark_by_id, get_all_landmarks
from app.services.images_service import get_all_images

LOCATIONS_FILE = "locations.json"
LANDMARKS_FILE = "landmarks.json"


def get_landmark_guide(landmark_id):
    """Return a single landmark enriched with its location and images."""
    landmark = get_landmark_by_id(landmark_id)
    location = get_location_by_id(landmark["location_id"])
    images = get_all_images(landmark_id=landmark_id)

    return {
        "landmark": landmark,
        "location": location,
        "images": images,
    }


def get_location_guide(location_id):
    """Return a location enriched with all of its landmarks (without images, for brevity)."""
    location = get_location_by_id(location_id)
    landmarks = get_all_landmarks(location_id=location_id)

    return {
        "location": location,
        "landmarks": landmarks,
    }


def search(query, limit=20):
    """
    Free-text search across locations and landmarks (English + Arabic names,
    descriptions, categories, regions). Simple case-insensitive substring
    match — intentionally simple for a hackathon prototype.
    """
    query_lower = query.lower()

    locations = data_loader.load(LOCATIONS_FILE)
    landmarks = data_loader.load(LANDMARKS_FILE)

    location_matches = [
        loc
        for loc in locations
        if query_lower in loc["name_en"].lower()
        or query_lower in loc["name_ar"]
        or query_lower in loc["region"].lower()
        or query_lower in loc["description"].lower()
    ]

    landmark_matches = [
        lm
        for lm in landmarks
        if query_lower in lm["name_en"].lower()
        or query_lower in lm["name_ar"]
        or query_lower in lm["category"].lower()
        or query_lower in lm["description"].lower()
    ]

    return {
        "query": query,
        "locations": location_matches[:limit],
        "landmarks": landmark_matches[:limit],
        "total_results": len(location_matches[:limit]) + len(landmark_matches[:limit]),
    }
