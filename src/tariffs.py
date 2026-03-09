"""Tariff fetching and filtering utilities."""

import json
from pathlib import Path

TARIFF_JSON_PATH = (
    Path(__file__).parent.parent / "sample_tariffs" / "sample_ausgrid_tariffs.json"
)


def fetch_all_tariffs() -> tuple[list[dict], dict]:
    """
    Load all available tariffs from the local JSON file.

    Returns:
        A tuple containing:
            - List of all tariff dictionaries
            - Dictionary with available filter options (types, distributors, states,
              customer_types)

    Raises:
        FileNotFoundError: If the tariff JSON file is not found.

    """
    with open(TARIFF_JSON_PATH, "r") as f:
        all_tariffs = json.load(f)

    # Extract unique values for each filter field (handle missing keys gracefully)
    filter_options = {
        "types": sorted(
            set(t["Type"] for t in all_tariffs if "Feed" not in t.get("Type", ""))
        ),
        "distributors": sorted(
            set(t.get("Distributor", "Unknown") for t in all_tariffs)
        ),
        "states": sorted(
            set(t.get("State", "Unknown") for t in all_tariffs if t.get("State"))
        ),
        "customer_types": sorted(
            set(t.get("CustomerType", "Unknown") for t in all_tariffs)
        ),
    }

    return all_tariffs, filter_options


def filter_tariffs(
    all_tariffs: list[dict],
    distributor: str | None = None,
    state: str | None = None,
    tariff_type: str | None = None,
    customer_type: str | None = None,
) -> list[dict]:
    """
    Filter tariffs based on specified criteria.

    Args:
        all_tariffs: List of all tariff dictionaries to filter.
        distributor: Filter by distributor/DNSP name. None means no filter.
        state: Filter by state (e.g., 'NSW', 'VIC'). None means no filter.
        tariff_type: Filter by tariff type (e.g., 'TOU', 'Single Rate').
            None means no filter.
        customer_type: Filter by customer type ('Residential', 'SmallBusiness').
            None means no filter.

    Returns:
        List of tariffs matching all specified criteria.

    """
    selected_tariffs = []

    for tariff in all_tariffs:
        # Skip feed-in tariffs (these are handled separately)
        if "Feed" in tariff.get("Type", ""):
            continue

        # Apply filters
        if distributor and tariff.get("Distributor") != distributor:
            continue
        if state and tariff.get("State") != state:
            continue
        if tariff_type and tariff.get("Type") != tariff_type:
            continue
        if customer_type and tariff.get("CustomerType") != customer_type:
            continue

        selected_tariffs.append(tariff)

    return selected_tariffs


def get_tariff_names(tariffs: list[dict]) -> list[str]:
    """
    Extract tariff names from a list of tariff dictionaries.

    Args:
        tariffs: List of tariff dictionaries.

    Returns:
        List of tariff names.

    """
    return [t.get("Name", f"Tariff {i}") for i, t in enumerate(tariffs)]


def _get_tariff_of_set_type(
    distributor: str, customer_type: str, tariff_type: str = "TOU"
) -> dict | None:
    """
    Retrieve the first tariff matching the given criteria.

    This is a convenience function that fetches all tariffs and returns the first
    match for the given distributor, customer type, and tariff type.

    Args:
        distributor: The DNSP name of the distributor.
        customer_type: The type of customer (Residential, SmallBusiness).
        tariff_type: The type of tariff to retrieve. Default is "TOU".

    Returns:
        The first matching tariff dictionary, or None if no match found.

    """
    all_tariffs, _ = fetch_all_tariffs()
    matching = filter_tariffs(
        all_tariffs,
        distributor=distributor,
        tariff_type=tariff_type,
        customer_type=customer_type,
    )
    return matching[0] if matching else None
