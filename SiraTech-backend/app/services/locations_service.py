from app.errors import NotFoundError
from app.services import data_loader

LOCATIONS_FILE = "locations.json"


def get_all_locations(region=None):
    locations = data_loader.load(LOCATIONS_FILE)
    if region:
        region_lower = region.lower()
        locations = [loc for loc in locations if loc["region"].lower() == region_lower]
    return locations


def get_location_by_id(location_id):
    locations = data_loader.load(LOCATIONS_FILE)
    for loc in locations:
        if loc["id"] == location_id:
            return loc
    raise NotFoundError(
        f"Location '{location_id}' was not found.",
        details={"location_id": location_id},
    )


def list_regions():
    locations = data_loader.load(LOCATIONS_FILE)
    return sorted({loc["region"] for loc in locations})
