# Metadata Corpus

This directory contains the synthetic legacy metadata corpus used by the test
suite. The corpus is generated into each test's temporary directory so the
repository keeps the fixture definitions, expected values and file writers in
source control without storing opaque binary images.

Covered fixture cases:

- JPEG with EXIF `DateTimeOriginal`
- TIFF container tag `DateTime`
- IPTC-IIM `DateCreated` and `TimeCreated`
- Embedded XMP packet
- Same-basename XMP sidecar
- PNG with eXIf chunk
- PNG with `iTXt`/`tEXt` chunks
- File without usable metadata
- File with conflicting EXIF and XMP metadata
