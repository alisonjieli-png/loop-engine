"""Write and strictly verify PNG images with the standard library only.

The creative families write small previews and texture maps, and package
tests read them back. A sandbox has no imaging library, so this module is the
whole PNG implementation they rely on: an encoder for 8-bit grayscale, gray
with alpha, RGB and RGBA, and a decoder that refuses anything it cannot prove
(a bad signature, a chunk whose CRC fails, chunks out of order, a data stream
that inflates to the wrong length, an unknown filter byte, trailing bytes).
Interlaced images and bit depths other than 8 and 16 are refused by name
rather than guessed. No pixel leaves the module unchecked.
"""
from __future__ import annotations

import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
#: Channels per PNG colour type: gray, RGB, palette index, gray with alpha, RGBA.
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
COLOUR_TYPES = {1: 0, 2: 4, 3: 2, 4: 6}
#: The largest image either side may describe, and the largest inflated stream; a decoder is bounded work.
MAXIMUM_SIDE = 16384
MAXIMUM_PIXELS = 64 * 1024 * 1024
MAXIMUM_CHUNK_BYTES = 64 * 1024 * 1024
#: Ancillary chunks a writer may add; anything else unknown and critical (upper-case first letter) is refused.
CRITICAL = (b"IHDR", b"PLTE", b"IDAT", b"IEND")


class PngError(ValueError):
    """A PNG that does not verify. ``reason`` is a closed code; the message adds detail."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _filtered(row: bytes, previous: bytes, stride: int) -> bytes:
    """The row under the filter whose output has the smallest sum of absolute values (the common heuristic)."""
    width = len(row)
    candidates = [bytes([0]) + row]
    sub = bytearray(width)
    up = bytearray(width)
    average = bytearray(width)
    paeth = bytearray(width)
    for index in range(width):
        left = row[index - stride] if index >= stride else 0
        above = previous[index]
        corner = previous[index - stride] if index >= stride else 0
        value = row[index]
        sub[index] = (value - left) & 0xFF
        up[index] = (value - above) & 0xFF
        average[index] = (value - ((left + above) >> 1)) & 0xFF
        paeth[index] = (value - _paeth(left, above, corner)) & 0xFF
    candidates += [bytes([1]) + bytes(sub), bytes([2]) + bytes(up), bytes([3]) + bytes(average),
                   bytes([4]) + bytes(paeth)]

    def cost(data: bytes) -> int:
        return sum(value if value < 128 else 256 - value for value in data[1:])

    return min(candidates, key=cost)


def encode(width: int, height: int, pixels: bytes, channels: int = 3, *, bit_depth: int = 8) -> bytes:
    """A PNG of ``height`` rows of ``width`` pixels, ``channels`` interleaved samples each, row-major from the top.

    ``pixels`` holds exactly width * height * channels samples (two bytes each, big-endian, at bit depth 16).
    The output is deterministic: the same samples always give the same bytes."""
    if type(width) is not int or type(height) is not int or not (0 < width <= MAXIMUM_SIDE and 0 < height <= MAXIMUM_SIDE):
        raise PngError("dimensions_invalid", f"{width}x{height}")
    if channels not in COLOUR_TYPES or bit_depth not in (8, 16):
        raise PngError("format_unsupported", f"channels {channels}, bit depth {bit_depth}")
    sample_bytes = bit_depth // 8
    stride = channels * sample_bytes
    if not isinstance(pixels, (bytes, bytearray)) or len(pixels) != width * height * stride:
        raise PngError("pixel_count_wrong", f"expected {width * height * stride} bytes")
    header = struct.pack(">IIBBBBB", width, height, bit_depth, COLOUR_TYPES[channels], 0, 0, 0)
    raw = bytearray()
    previous = bytes(width * stride)
    for y in range(height):
        row = bytes(pixels[y * width * stride:(y + 1) * width * stride])
        raw += _filtered(row, previous, stride)
        previous = row
    return (SIGNATURE + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def _unfilter(raw: bytes, width: int, height: int, stride: int) -> bytes:
    row_bytes = width * stride
    out = bytearray(row_bytes * height)
    previous = bytearray(row_bytes)
    position = 0
    for y in range(height):
        kind = raw[position]
        position += 1
        line = bytearray(raw[position:position + row_bytes])
        position += row_bytes
        if kind == 1:
            for index in range(stride, row_bytes):
                line[index] = (line[index] + line[index - stride]) & 0xFF
        elif kind == 2:
            for index in range(row_bytes):
                line[index] = (line[index] + previous[index]) & 0xFF
        elif kind == 3:
            for index in range(row_bytes):
                left = line[index - stride] if index >= stride else 0
                line[index] = (line[index] + ((left + previous[index]) >> 1)) & 0xFF
        elif kind == 4:
            for index in range(row_bytes):
                left = line[index - stride] if index >= stride else 0
                corner = previous[index - stride] if index >= stride else 0
                line[index] = (line[index] + _paeth(left, previous[index], corner)) & 0xFF
        elif kind != 0:
            raise PngError("filter_invalid", f"row {y} uses filter {kind}")
        out[y * row_bytes:(y + 1) * row_bytes] = line
        previous = line
    return bytes(out)


def decode(data: bytes) -> dict:
    """Verify every structural rule and return width, height, channels, bit_depth, palette and samples.

    Palette images keep their indices in ``pixels`` and their colours in ``palette`` (a list of RGB tuples)."""
    if not isinstance(data, (bytes, bytearray)) or not data.startswith(SIGNATURE):
        raise PngError("signature_invalid")
    position, chunks, seen = len(SIGNATURE), [], []
    while position < len(data):
        if position + 8 > len(data):
            raise PngError("chunk_truncated", f"at byte {position}")
        length, kind = struct.unpack(">I4s", data[position:position + 8])
        if length > MAXIMUM_CHUNK_BYTES or position + 12 + length > len(data):
            raise PngError("chunk_truncated", f"{kind!r} at byte {position}")
        payload = data[position + 8:position + 8 + length]
        (crc,) = struct.unpack(">I", data[position + 8 + length:position + 12 + length])
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise PngError("crc_mismatch", repr(kind))
        if not kind.isalpha():
            raise PngError("chunk_name_invalid", repr(kind))
        if kind[:1].isupper() and kind not in CRITICAL:
            raise PngError("unknown_critical_chunk", repr(kind))
        chunks.append((kind, payload))
        seen.append(kind)
        position += 12 + length
        if kind == b"IEND":
            break
    if position != len(data):
        raise PngError("trailing_bytes", f"{len(data) - position} after IEND")
    if not seen or seen[0] != b"IHDR" or seen[-1] != b"IEND" or seen.count(b"IHDR") != 1 or seen.count(b"IEND") != 1:
        raise PngError("chunk_order_invalid", ",".join(kind.decode("latin-1") for kind in seen[:8]))
    idat = [index for index, kind in enumerate(seen) if kind == b"IDAT"]
    if not idat or idat != list(range(idat[0], idat[-1] + 1)):
        raise PngError("idat_not_contiguous")
    header = chunks[0][1]
    if len(header) != 13:
        raise PngError("header_invalid", "IHDR length")
    width, height, bit_depth, colour, compression, filtering, interlace = struct.unpack(">IIBBBBB", header)
    if not (0 < width <= MAXIMUM_SIDE and 0 < height <= MAXIMUM_SIDE) or width * height > MAXIMUM_PIXELS:
        raise PngError("dimensions_invalid", f"{width}x{height}")
    if colour not in CHANNELS or compression != 0 or filtering != 0:
        raise PngError("header_invalid", f"colour {colour}, compression {compression}, filter {filtering}")
    if interlace != 0:
        raise PngError("interlace_unsupported")
    if bit_depth not in (8, 16) or (colour == 3 and bit_depth != 8):
        raise PngError("bit_depth_unsupported", str(bit_depth))
    palette = None
    if colour == 3:
        entries = [payload for kind, payload in chunks if kind == b"PLTE"]
        if len(entries) != 1 or len(entries[0]) % 3 or not 0 < len(entries[0]) <= 768:
            raise PngError("palette_invalid")
        palette = [tuple(entries[0][index:index + 3]) for index in range(0, len(entries[0]), 3)]
    channels = CHANNELS[colour]
    stride = channels * bit_depth // 8
    expected = height * (1 + width * stride)
    inflater = zlib.decompressobj()
    try:
        raw = inflater.decompress(b"".join(chunks[index][1] for index in idat), expected + 1)
    except zlib.error as error:
        raise PngError("data_stream_invalid", str(error)) from None
    if len(raw) != expected or not inflater.eof or inflater.unconsumed_tail:
        raise PngError("data_length_wrong", f"inflated {len(raw)} of {expected} bytes")
    pixels = _unfilter(raw, width, height, stride)
    if palette is not None and any(index >= len(palette) for index in pixels):
        raise PngError("palette_index_out_of_range")
    return {"width": width, "height": height, "channels": channels, "bit_depth": bit_depth,
            "colour_type": colour, "palette": palette, "pixels": pixels}


def statistics(image: dict) -> dict:
    """Per-channel minimum, maximum and mean of an 8-bit decoded image, for content checks (not a quality score)."""
    if image["bit_depth"] != 8:
        raise PngError("bit_depth_unsupported", "statistics read 8-bit images")
    channels, pixels = image["channels"], image["pixels"]
    count = image["width"] * image["height"]
    rows = []
    for channel in range(channels):
        values = pixels[channel::channels]
        rows.append({"minimum": min(values), "maximum": max(values), "mean": round(sum(values) / count, 4)})
    return {"channels": rows, "pixels": count}


__all__ = ["PngError", "SIGNATURE", "encode", "decode", "statistics"]
