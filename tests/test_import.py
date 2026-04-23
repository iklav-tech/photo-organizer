from photo_organizer import __version__


def test_package_version_is_string() -> None:
    assert isinstance(__version__, str)
    assert __version__
