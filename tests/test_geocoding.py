import io
import json
import logging
from urllib.error import HTTPError, URLError

from photo_organizer.geocoding import (
    ReverseGeocodedLocation,
    reverse_geocode_coordinates,
)
from photo_organizer.metadata import GPSCoordinates


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_reverse_geocode_coordinates_resolves_readable_location() -> None:
    requests = []

    def opener(request, timeout):
        requests.append((request, timeout))
        return FakeResponse(
            {
                "address": {
                    "city": "Sao Paulo",
                    "state": "Sao Paulo",
                    "country": "Brazil",
                }
            }
        )

    result = reverse_geocode_coordinates(
        GPSCoordinates(latitude=-23.5, longitude=-46.625),
        opener=opener,
        timeout=2.0,
    )

    assert result == ReverseGeocodedLocation(
        city="Sao Paulo",
        state="Sao Paulo",
        country="Brazil",
    )
    assert requests[0][1] == 2.0
    assert "lat=-23.50000000" in requests[0][0].full_url
    assert "lon=-46.62500000" in requests[0][0].full_url


def test_reverse_geocode_coordinates_uses_city_fallbacks() -> None:
    def opener(_request, timeout):
        return FakeResponse(
            {
                "address": {
                    "town": "Paraty",
                    "state": "Rio de Janeiro",
                    "country": "Brazil",
                }
            }
        )

    result = reverse_geocode_coordinates(
        GPSCoordinates(latitude=-23.2, longitude=-44.7),
        opener=opener,
    )

    assert result == ReverseGeocodedLocation(
        city="Paraty",
        state="Rio de Janeiro",
        country="Brazil",
    )


def test_reverse_geocode_coordinates_returns_none_when_disabled() -> None:
    def fail_if_called(_request, timeout):
        raise AssertionError("network must not be called when reverse geocoding is disabled")

    result = reverse_geocode_coordinates(
        GPSCoordinates(latitude=-23.5, longitude=-46.625),
        enabled=False,
        opener=fail_if_called,
    )

    assert result is None


def test_reverse_geocode_coordinates_handles_network_failure(caplog) -> None:
    def opener(_request, timeout):
        raise URLError("temporary failure")

    with caplog.at_level(logging.WARNING):
        result = reverse_geocode_coordinates(
            GPSCoordinates(latitude=-23.5, longitude=-46.625),
            opener=opener,
        )

    assert result is None
    assert "Reverse geocoding failed" in caplog.text


def test_reverse_geocode_coordinates_handles_service_limit(caplog) -> None:
    def opener(_request, timeout):
        raise HTTPError(
            url="https://example.test",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(),
        )

    with caplog.at_level(logging.WARNING):
        result = reverse_geocode_coordinates(
            GPSCoordinates(latitude=-23.5, longitude=-46.625),
            opener=opener,
        )

    assert result is None
    assert "status=429" in caplog.text
