from app.errors import NotFoundError
from app.services import data_loader
from app.services.landmarks_service import get_landmark_by_id

IMAGES_FILE = "images.json"


def get_all_images(landmark_id=None):
    images = data_loader.load(IMAGES_FILE)

    if landmark_id:
        # Raises NotFoundError itself if the landmark doesn't exist.
        get_landmark_by_id(landmark_id)
        images = [img for img in images if img["landmark_id"] == landmark_id]

    return images


def get_image_by_id(image_id):
    images = data_loader.load(IMAGES_FILE)
    for img in images:
        if img["id"] == image_id:
            return img
    raise NotFoundError(
        f"Image '{image_id}' was not found.",
        details={"image_id": image_id},
    )
