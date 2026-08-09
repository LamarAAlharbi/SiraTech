from app.errors import NotFoundError
from app.services import data_loader
from app.services.locations_service import get_location_by_id

LANDMARKS_FILE = "landmarks.json"


def get_all_landmarks(location_id=None, category=None, unesco_only=False):
    landmarks = data_loader.load(LANDMARKS_FILE)

    if location_id:
        # Raises NotFoundError itself if the location doesn't exist, giving
        # a clearer error than silently returning an empty list.
        get_location_by_id(location_id)
        landmarks = [lm for lm in landmarks if lm["location_id"] == location_id]

    if category:
        category_lower = category.lower()
        landmarks = [lm for lm in landmarks if lm["category"].lower() == category_lower]

    if unesco_only:
        landmarks = [lm for lm in landmarks if lm["unesco"] is True]

    return landmarks


def get_landmark_by_id(landmark_id):
    landmarks = data_loader.load(LANDMARKS_FILE)
    for lm in landmarks:
        if lm["id"] == landmark_id:
            return lm
    raise NotFoundError(
        f"Landmark '{landmark_id}' was not found.",
        details={"landmark_id": landmark_id},
    )


def list_categories():
    landmarks = data_loader.load(LANDMARKS_FILE)
    return sorted({lm["category"] for lm in landmarks})
