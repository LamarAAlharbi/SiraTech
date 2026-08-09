"""
"See the Past" historical-image endpoints.

Product rule: these endpoints only ever serve curated/verified records from
app/data/historical_images.json — nothing here calls Gemini or any other
GenAI model, and no historical photograph is ever generated. Until the
content team adds real, rights-cleared images, every record returned is
sample placeholder data, and every response is clearly labeled as such via
`sample_data` (response-level) and `is_sample` (per-record).
"""

from flask import Blueprint, jsonify, request

from app.services import history_service
from app.utils.validation import get_str_arg

history_bp = Blueprint("history", __name__, url_prefix="/api/history")


def _sample_data_status(records):
    """
    Classify a set of records as "all", "some", or "none" sample data.

    An empty result set is reported as "none" — there's no sample data to
    warn about, as distinct from a landmark whose images are all samples.
    """
    if not records:
        return "none"

    sample_count = sum(1 for r in records if r.get("is_sample"))
    if sample_count == len(records):
        return "all"
    if sample_count > 0:
        return "some"
    return "none"


_SAMPLE_DATA_NOTICES = {
    "all": (
        "All of these records are placeholder data for prototyping the See the Past "
        "feature. None are real historical photographs and none carry a verified "
        "source — do not treat them as authentic."
    ),
    "some": (
        "Some of these records are placeholder data for prototyping the See the Past "
        "feature (see each record's is_sample flag). Only records with "
        "\"is_sample\": false are verified historical photographs."
    ),
    "none": None,
}


@history_bp.get("/landmarks/<string:landmark_id>")
def history_for_landmark(landmark_id):
    tag = get_str_arg(request.args, "tag", choices=history_service.ALLOWED_TAGS)

    records = history_service.get_history_images_for_landmark(landmark_id, tag=tag)
    status = _sample_data_status(records)

    return jsonify(
        {
            "landmark_id": landmark_id,
            "count": len(records),
            "sample_data": status,
            "sample_data_notice": _SAMPLE_DATA_NOTICES[status],
            "results": records,
        }
    )


@history_bp.get("/images/<string:image_id>")
def history_image(image_id):
    record = history_service.get_history_image_by_id(image_id)

    response = dict(record)
    if record.get("is_sample"):
        response["sample_data_notice"] = (
            "This is a placeholder record for prototyping the See the Past feature. "
            "It is not a real historical photograph and carries no verified source — "
            "do not treat it as authentic."
        )
    return jsonify(response)
