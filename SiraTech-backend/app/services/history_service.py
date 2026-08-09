"""
"See the Past" historical-image lookups.

Product rule: historical photographs are NEVER generated with GenAI. This
service only ever reads from a curated/verified data file
(app/data/historical_images.json). Until the content team adds real,
rights-cleared archival images, that file holds sample placeholder records
only — every one of them is flagged `is_sample: true` and carries no
invented source URL or authenticity claim (see the file itself for the
placeholder wording used).

This is a distinct dataset from app/data/images.json (present-day landmark
photos served by /api/v1/images) — historical records need extra fields
(year/period, tags, rights/license) that present-day gallery photos don't.
"""

from app.errors import NotFoundError
from app.services import data_loader
from app.services.landmarks_service import get_landmark_by_id

HISTORY_IMAGES_FILE = "historical_images.json"

# Allowed values for the `tags` field on a historical-image record.
ALLOWED_TAGS = ("architecture", "fashion", "daily_life", "event")


def get_history_images_for_landmark(landmark_id, tag=None):
    """
    Return all curated historical-image records for a landmark.

    Raises NotFoundError if the landmark itself doesn't exist (same
    behavior as every other landmark_id-scoped lookup in this API).
    """
    # Confirms the landmark exists; raises NotFoundError itself if not.
    get_landmark_by_id(landmark_id)

    records = data_loader.load(HISTORY_IMAGES_FILE)
    results = [r for r in records if r["landmark_id"] == landmark_id]

    if tag:
        results = [r for r in results if tag in r.get("tags", [])]

    return results


def get_history_image_by_id(image_id):
    """Return a single curated historical-image record by id."""
    records = data_loader.load(HISTORY_IMAGES_FILE)
    for record in records:
        if record["id"] == image_id:
            return record
    raise NotFoundError(
        f"Historical image '{image_id}' was not found.",
        details={"image_id": image_id},
    )
