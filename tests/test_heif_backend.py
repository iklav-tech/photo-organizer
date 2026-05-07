from photo_organizer.heif_backend import PillowHeifBackend


class FakeHeifImage:
    def __init__(self, *, size=(10, 10), mode="RGB", info=None):
        self.size = size
        self.mode = mode
        self.info = info or {}


class FakeHeifFile:
    def __init__(self, images, *, primary_index=None, mimetype="image/heic"):
        self._images = images
        self.primary_index = primary_index
        self.mimetype = mimetype

    def __iter__(self):
        return iter(self._images)


class FakePillowHeifModule:
    def __init__(self, heif_file):
        self.heif_file = heif_file

    def register_heif_opener(self):
        return None

    def open_heif(self, _path):
        return self.heif_file


def test_read_metadata_selects_primary_image_deterministically(monkeypatch) -> None:
    first = FakeHeifImage(info={"primary": False, "exif": b"first"})
    second = FakeHeifImage(info={"primary": True, "exif": b"second"})
    heif_file = FakeHeifFile([first, second], primary_index=0)

    monkeypatch.setattr(
        PillowHeifBackend,
        "_load_pillow_heif",
        lambda _self: FakePillowHeifModule(heif_file),
    )

    result = PillowHeifBackend().read_metadata("image.heic")

    assert result.exif == b"second"


def test_read_container_info_reports_complex_heif_structure(monkeypatch) -> None:
    first = FakeHeifImage(
        size=(4000, 3000),
        info={
            "primary": True,
            "bit_depth": 10,
            "metadata": [{"type": "mime"}],
            "thumbnails": [object()],
            "aux": {"urn:mpeg:hevc:2015:auxid:1": object()},
        },
    )
    second = FakeHeifImage(size=(1024, 768), info={"depth_images": [object()]})
    heif_file = FakeHeifFile([first, second], primary_index=0)

    monkeypatch.setattr(
        PillowHeifBackend,
        "_load_pillow_heif",
        lambda _self: FakePillowHeifModule(heif_file),
    )

    result = PillowHeifBackend().read_container_info("image.heic")

    assert result.image_count == 2
    assert result.primary_index == 0
    assert result.selected_image_index == 0
    assert result.images[0].width == 4000
    assert result.images[0].bit_depth == 10
    assert result.is_complex is True
    assert result.unsupported_features == (
        "multiple images or sequence: only the selected primary image is processed",
        "embedded thumbnails: not extracted",
        "auxiliary images: not extracted",
        "depth images: not extracted",
    )


def test_read_container_info_reports_primary_selection_fallback(monkeypatch) -> None:
    heif_file = FakeHeifFile([FakeHeifImage(), FakeHeifImage()], primary_index=None)

    monkeypatch.setattr(
        PillowHeifBackend,
        "_load_pillow_heif",
        lambda _self: FakePillowHeifModule(heif_file),
    )

    result = PillowHeifBackend().read_container_info("image.heic")

    assert result.selected_image_index == 0
    assert result.warnings == (
        "primary image not exposed by backend; selected image index 0",
    )
