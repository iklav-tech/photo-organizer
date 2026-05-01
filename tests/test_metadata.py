from datetime import datetime
from pathlib import Path
import sys
import types
import logging

import photo_organizer.metadata as metadata


def test_metadata_precedence_policy_covers_required_fields() -> None:
    fields = {
        rule.field
        for rule in metadata.get_metadata_precedence_policy()
    }

    assert fields == {
        "date_taken",
        "location",
        "title",
        "author",
        "description",
    }


def test_metadata_precedence_policy_declares_roles_and_support_status() -> None:
    for field in ("date_taken", "location", "title", "author", "description"):
        rules = metadata.get_metadata_precedence_policy(field)

        assert rules
        assert rules[0].role == "primary"
        assert all(rule.role in {"primary", "fallback", "heuristic"} for rule in rules)
        assert all(rule.support in {"implemented", "planned"} for rule in rules)


def test_date_taken_policy_orders_primary_fallback_and_heuristic_sources() -> None:
    rules = metadata.get_metadata_precedence_policy("date_taken")

    assert [(rule.role, rule.source, rule.keys) for rule in rules] == [
        ("primary", "EXIF", ("DateTimeOriginal",)),
        ("fallback", "EXIF", ("CreateDate", "DateTime", "DateTimeDigitized")),
        ("fallback", "XMP", ("exif:DateTimeOriginal", "xmp:CreateDate")),
        ("fallback", "IPTC-IIM", ("DateCreated", "TimeCreated")),
        ("fallback", "PNG metadata", ("Creation Time", "CreationTime")),
        ("heuristic", "Filesystem", ("mtime",)),
    ]


def test_location_policy_distinguishes_gps_source_and_reverse_geocoding() -> None:
    rules = metadata.get_metadata_precedence_policy("location")

    assert [(rule.role, rule.source) for rule in rules] == [
        ("primary", "EXIF"),
        ("fallback", "XMP"),
        ("fallback", "IPTC-IIM"),
        ("heuristic", "Reverse geocoding"),
    ]


def test_extract_exif_metadata_reads_compatible_jpeg_exif(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    class FakeImage:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getexif(self):
            return {
                36867: "2024:01:02 03:04:05",
                306: "2024:01:02 03:04:05",
            }

    fake_image_module = types.SimpleNamespace(open=lambda _path: FakeImage())
    fake_exif_tags_module = types.SimpleNamespace(
        TAGS={36867: "DateTimeOriginal", 306: "DateTime"}
    )
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    result = metadata.extract_exif_metadata(file_path)

    assert result["DateTimeOriginal"] == "2024:01:02 03:04:05"


def test_extract_xmp_metadata_reads_relevant_fields_and_namespaces(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_bytes(
        b"prefix"
        b"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description
      xmlns:xmp="http://ns.adobe.com/xap/1.0/"
      xmlns:exif="http://ns.adobe.com/exif/1.0/"
      xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
      xmp:CreateDate="2024-08-15T14:32:09"
      exif:GPSLatitude="23,30.000S"
      exif:GPSLongitude="46,37.500W"
      photoshop:City="Sao Paulo" />
  </rdf:RDF>
</x:xmpmeta>"""
        b"suffix"
    )

    result = metadata.extract_xmp_metadata(file_path)

    assert result["xmp:CreateDate"] == "2024-08-15T14:32:09"
    assert result["exif:GPSLatitude"] == "23,30.000S"
    assert result["exif:GPSLongitude"] == "46,37.500W"
    assert result["photoshop:City"] == "Sao Paulo"
    assert result["XMPNamespaces"]["xmp"] == "http://ns.adobe.com/xap/1.0/"
    assert result["XMPNamespaces"]["exif"] == "http://ns.adobe.com/exif/1.0/"
    assert result["XMPNamespaces"]["photoshop"] == "http://ns.adobe.com/photoshop/1.0/"


def test_extract_xmp_metadata_handles_xml_parse_errors_safely(
    tmp_path: Path,
    caplog,
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_bytes(
        b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF></x:xmpmeta>'
    )

    with caplog.at_level(logging.WARNING):
        result = metadata.extract_xmp_metadata(file_path)

    assert result == {}
    assert "Failed to parse XMP" in caplog.text


def test_get_best_available_datetime_uses_xmp_when_exif_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_bytes(
        b"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description
      xmlns:xmp="http://ns.adobe.com/xap/1.0/"
      xmp:CreateDate="2024-08-15T14:32:09" />
  </rdf:RDF>
</x:xmpmeta>"""
    )
    monkeypatch.setattr(metadata, "_read_exif_datetime_fields", lambda _path: {})

    resolution = metadata.resolve_best_available_datetime(file_path)

    assert resolution.value == datetime(2024, 8, 15, 14, 32, 9)
    assert resolution.used_fallback is False
    assert resolution.provenance == metadata.MetadataProvenance(
        source="XMP",
        field="xmp:CreateDate",
        confidence="medium",
        raw_value="2024-08-15T14:32:09",
    )


def test_extract_gps_coordinates_uses_xmp_when_exif_gps_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_bytes(
        b"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description
      xmlns:exif="http://ns.adobe.com/exif/1.0/"
      exif:GPSLatitude="23,30.000S"
      exif:GPSLongitude="46,37.500W" />
  </rdf:RDF>
</x:xmpmeta>"""
    )
    monkeypatch.setattr(metadata, "extract_exif_metadata", lambda _path: {})

    result = metadata.extract_gps_coordinates(file_path)

    assert result == metadata.GPSCoordinates(latitude=-23.5, longitude=-46.625)
    assert result is not None
    assert result.provenance == metadata.MetadataProvenance(
        source="XMP",
        field="exif:GPSLatitude,exif:GPSLongitude",
        confidence="medium",
        raw_value={
            "exif:GPSLatitude": "23,30.000S",
            "exif:GPSLongitude": "46,37.500W",
            "exif:GPSLatitudeRef": None,
            "exif:GPSLongitudeRef": None,
        },
    )


def test_extract_exif_metadata_reads_gps_coordinates_as_decimal(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    class FakeImage:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getexif(self):
            return {
                34853: {
                    1: "N",
                    2: ((23, 1), (30, 1), (0, 1)),
                    3: "W",
                    4: ((46, 1), (37, 1), (30, 1)),
                },
            }

    fake_image_module = types.SimpleNamespace(open=lambda _path: FakeImage())
    fake_exif_tags_module = types.SimpleNamespace(
        TAGS={34853: "GPSInfo"},
        GPSTAGS={
            1: "GPSLatitudeRef",
            2: "GPSLatitude",
            3: "GPSLongitudeRef",
            4: "GPSLongitude",
        },
    )
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    result = metadata.extract_exif_metadata(file_path)

    assert result["GPSLatitudeDecimal"] == 23.5
    assert result["GPSLongitudeDecimal"] == -46.625


def test_extract_exif_metadata_reads_gps_coordinates_from_ifd_pointer(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    class FakeExif:
        def __bool__(self):
            return True

        def items(self):
            return [(34853, 1352)]

        def get_ifd(self, key):
            assert key == 34853
            return {
                1: "N",
                2: (26.0, 34.951, 0.0),
                3: "W",
                4: (80.0, 12.014, 0.0),
            }

    class FakeImage:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getexif(self):
            return FakeExif()

    fake_image_module = types.SimpleNamespace(open=lambda _path: FakeImage())
    fake_exif_tags_module = types.SimpleNamespace(
        TAGS={34853: "GPSInfo"},
        GPSTAGS={
            1: "GPSLatitudeRef",
            2: "GPSLatitude",
            3: "GPSLongitudeRef",
            4: "GPSLongitude",
        },
    )
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    result = metadata.extract_exif_metadata(file_path)

    assert result["GPSLatitudeDecimal"] == 26.582516666666666
    assert result["GPSLongitudeDecimal"] == -80.20023333333333


def test_extract_gps_coordinates_returns_decimal_coordinates(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    monkeypatch.setattr(
        metadata,
        "extract_exif_metadata",
        lambda _path: {
            "GPSInfo": {
                "GPSLatitudeRef": "S",
                "GPSLatitude": (12, 15, 30),
                "GPSLongitudeRef": "E",
                "GPSLongitude": (45, 30, 0),
            },
        },
    )

    result = metadata.extract_gps_coordinates(file_path)

    assert result == metadata.GPSCoordinates(latitude=-12.258333333333333, longitude=45.5)
    assert result is not None
    assert result.provenance == metadata.MetadataProvenance(
        source="EXIF",
        field="GPSInfo",
        confidence="high",
        raw_value={
            "GPSLatitudeRef": "S",
            "GPSLatitude": (12, 15, 30),
            "GPSLongitudeRef": "E",
            "GPSLongitude": (45, 30, 0),
        },
    )


def test_extract_gps_coordinates_returns_none_without_gps(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    monkeypatch.setattr(metadata, "extract_exif_metadata", lambda _path: {})

    result = metadata.extract_gps_coordinates(file_path)

    assert result is None


def test_extract_exif_metadata_returns_empty_when_no_exif(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    class FakeImage:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getexif(self):
            return {}

    fake_image_module = types.SimpleNamespace(open=lambda _path: FakeImage())
    fake_exif_tags_module = types.SimpleNamespace(TAGS={})
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    result = metadata.extract_exif_metadata(file_path)

    assert result == {}


def test_extract_exif_metadata_skips_formats_without_real_exif_support(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.bmp"
    file_path.write_text("x")

    def fail_if_opened(_path):
        raise AssertionError("BMP should not be opened for EXIF extraction")

    fake_image_module = types.SimpleNamespace(open=fail_if_opened)
    fake_exif_tags_module = types.SimpleNamespace(TAGS={})
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    result = metadata.extract_exif_metadata(file_path)

    assert result == {}


def test_extract_exif_metadata_handles_read_exceptions_safely(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    def raise_open(_path):
        raise OSError("cannot read")

    fake_image_module = types.SimpleNamespace(open=raise_open)
    fake_exif_tags_module = types.SimpleNamespace(TAGS={})
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    result = metadata.extract_exif_metadata(file_path)

    assert result == {}


def test_extract_exif_metadata_handles_malformed_exif_safely(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    class MalformedExif:
        def __bool__(self):
            return True

        def items(self):
            raise ValueError("malformed exif")

    class FakeImage:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getexif(self):
            return MalformedExif()

    fake_image_module = types.SimpleNamespace(open=lambda _path: FakeImage())
    fake_exif_tags_module = types.SimpleNamespace(TAGS={})
    fake_pil_module = types.SimpleNamespace(
        Image=fake_image_module,
        ExifTags=fake_exif_tags_module,
    )

    monkeypatch.setitem(sys.modules, "PIL", fake_pil_module)

    with caplog.at_level(logging.WARNING):
        result = metadata.extract_exif_metadata(file_path)

    assert result == {}
    assert "Failed to parse EXIF" in caplog.text
    assert "malformed exif" in caplog.text


def test_get_best_available_datetime_prioritizes_datetimeoriginal(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    monkeypatch.setattr(
        metadata,
        "_read_exif_datetime_fields",
        lambda _path: {
            "DateTimeOriginal": "2024:01:02 03:04:05",
            "CreateDate": "2020:01:01 00:00:00",
        },
    )

    result = metadata.get_best_available_datetime(file_path)

    assert result == datetime(2024, 1, 2, 3, 4, 5)
    assert isinstance(result, datetime)

    resolution = metadata.resolve_best_available_datetime(file_path)
    assert resolution.provenance == metadata.MetadataProvenance(
        source="EXIF",
        field="DateTimeOriginal",
        confidence="high",
        raw_value="2024:01:02 03:04:05",
    )


def test_get_best_available_datetime_uses_createdate_as_second_option(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    monkeypatch.setattr(
        metadata,
        "_read_exif_datetime_fields",
        lambda _path: {
            "CreateDate": "2021:06:07 08:09:10",
        },
    )

    result = metadata.get_best_available_datetime(file_path)

    assert result == datetime(2021, 6, 7, 8, 9, 10)
    assert isinstance(result, datetime)

    resolution = metadata.resolve_best_available_datetime(file_path)
    assert resolution.provenance == metadata.MetadataProvenance(
        source="EXIF",
        field="CreateDate",
        confidence="medium",
        raw_value="2021:06:07 08:09:10",
    )


def test_get_best_available_datetime_falls_back_to_file_modification_time(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")

    monkeypatch.setattr(metadata, "_read_exif_datetime_fields", lambda _path: {})

    expected_dt = datetime(2022, 9, 10, 11, 12, 13)
    timestamp = expected_dt.timestamp()
    file_path.touch()
    file_path.chmod(0o644)
    # Keep atime unchanged and force mtime to a deterministic timestamp.
    file_path.stat()
    import os

    os.utime(file_path, (timestamp, timestamp))

    result = metadata.get_best_available_datetime(file_path)

    assert result == datetime.fromtimestamp(timestamp)
    assert isinstance(result, datetime)

    resolution = metadata.resolve_best_available_datetime(file_path)
    assert resolution.provenance == metadata.MetadataProvenance(
        source="filesystem",
        field="mtime",
        confidence="low",
        raw_value=timestamp,
    )


def test_get_best_available_datetime_logs_fallback_decision(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    file_path = tmp_path / "image.jpg"
    file_path.write_text("x")
    monkeypatch.setattr(metadata, "_read_exif_datetime_fields", lambda _path: {})

    with caplog.at_level(logging.INFO):
        metadata.get_best_available_datetime(file_path)

    assert "Datetime fallback to file modification time" in caplog.text
