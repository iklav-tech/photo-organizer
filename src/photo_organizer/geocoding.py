"""Reverse geocoding helpers for GPS metadata."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from photo_organizer import __version__
from photo_organizer.metadata import GPSCoordinates


logger = logging.getLogger(__name__)

DEFAULT_REVERSE_GEOCODING_URL = "https://nominatim.openstreetmap.org/reverse"
DEFAULT_USER_AGENT = f"photo-organizer/{__version__}"


@dataclass(frozen=True)
class ReverseGeocodedLocation:
    """Human-readable location resolved from GPS coordinates."""

    city: str | None
    state: str | None
    country: str | None


def _build_reverse_geocoding_url(
    coordinates: GPSCoordinates,
    service_url: str,
) -> str:
    query = urlencode(
        {
            "format": "jsonv2",
            "lat": f"{coordinates.latitude:.8f}",
            "lon": f"{coordinates.longitude:.8f}",
            "addressdetails": "1",
        }
    )
    return f"{service_url}?{query}"


def _location_from_payload(payload: dict[str, Any]) -> ReverseGeocodedLocation | None:
    address = payload.get("address")
    if not isinstance(address, dict):
        return None

    city = next(
        (
            address.get(key)
            for key in ("city", "town", "village", "municipality", "county")
            if address.get(key)
        ),
        None,
    )
    state = address.get("state") or address.get("region")
    country = address.get("country")

    if city is None and state is None and country is None:
        return None

    return ReverseGeocodedLocation(city=city, state=state, country=country)


def reverse_geocode_coordinates(
    coordinates: GPSCoordinates | None,
    *,
    enabled: bool = True,
    timeout: float = 5.0,
    service_url: str = DEFAULT_REVERSE_GEOCODING_URL,
    opener: Any = urlopen,
) -> ReverseGeocodedLocation | None:
    """Resolve GPS coordinates into city, state and country.

    Network, service-limit and malformed-response failures are logged and
    treated as missing location data.
    """
    if not enabled or coordinates is None:
        return None

    url = _build_reverse_geocoding_url(coordinates, service_url)
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        },
    )

    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        logger.warning(
            "Reverse geocoding service returned an error: status=%s reason=%s",
            exc.code,
            exc.reason,
        )
        return None
    except (URLError, TimeoutError, OSError) as exc:
        logger.warning("Reverse geocoding failed: error=%s", exc)
        return None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Reverse geocoding returned an invalid response: error=%s", exc)
        return None

    if not isinstance(payload, dict):
        logger.warning("Reverse geocoding returned an unexpected response")
        return None

    return _location_from_payload(payload)
