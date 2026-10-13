"""Opt-in qualification of small self-contained H.264/AAC MP4 resources.

This is a decoder adapter within component qualification, not a media runtime.
It reads exact package bytes, refuses unsupported structure, then probes and
fully decodes them with explicitly pinned tools inside a networkless sandbox.
Format validity does not establish media rights, visual quality or usefulness.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import struct
import subprocess
import time
import unicodedata

from .sandbox import SandboxLimits, _limits
from loop_engine.core.service_runtime.catalogue_packages import MAXIMUM_FILE_BYTES

PROFILE = "self_contained_h264_aac_mp4/v2"
MANIFEST_NAME = "resource-media.json"
MANIFEST_VERSION = "component_media_resources/v1"
MAX_FILE_BYTES = MAXIMUM_FILE_BYTES
MAX_BOXES = 4096
MAX_DEPTH = 12
MAX_SIDE = 1920
MAX_PIXELS = 1920 * 1080
MAX_SECONDS = 120
MAX_FPS = 60
MAX_FRAMES = MAX_SECONDS * MAX_FPS
MAX_SAMPLES = MAX_FRAMES + 2  # AAC-LC at 48 kHz has fewer samples/packets than 60 fps, plus priming.
MAX_TOOL_BYTES = 192 * 1024 * 1024
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
WALL_SECONDS = 45
TMP_BYTES = 8 * 1024 * 1024
LIMITS = SandboxLimits(cpu_seconds=35, memory_bytes=768 * 1024 * 1024,
                       file_bytes=MAX_TOOL_BYTES, open_files=64, wall_seconds=WALL_SECONDS)
_HEX = re.compile(r"[0-9a-f]{64}")
_CONTAINERS = {
    b"moov": {b"mvhd", b"trak", b"udta"}, b"trak": {b"tkhd", b"edts", b"mdia"},
    b"edts": {b"elst"}, b"mdia": {b"mdhd", b"hdlr", b"minf"},
    b"minf": {b"vmhd", b"smhd", b"dinf", b"stbl"}, b"dinf": {b"dref"},
    b"stbl": {b"stsd", b"stts", b"stss", b"ctts", b"stsc", b"stsz", b"stco", b"co64", b"sgpd", b"sbgp"},
    b"udta": {b"meta"}, b"meta": {b"hdlr", b"ilst"}, b"ilst": {b"\xa9too", b"\xa9nam"},
    b"\xa9too": {b"data"}, b"\xa9nam": {b"data"},
}


class MediaValidationError(ValueError):
    """A closed refusal code without decoder output or source metadata."""
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def require(value, reason):
    if not value:
        raise MediaValidationError(reason)


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            require(key not in result, "duplicate_json_key")
            result[key] = item
        return result
    try:
        return json.loads(value, object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(MediaValidationError("nonfinite_json")))
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, MediaValidationError):
            raise
        raise MediaValidationError("invalid_json") from None


@dataclass(frozen=True)
class MediaTools:
    ffmpeg: str
    ffmpeg_sha256: str
    ffprobe: str
    ffprobe_sha256: str
    bwrap: str = "/usr/bin/bwrap"

    def __post_init__(self):
        require(self.bwrap == "/usr/bin/bwrap", "sandbox_launcher_unqualified")
        for path in (self.ffmpeg, self.ffprobe, self.bwrap):
            require(type(path) is str and os.path.isabs(path) and ".." not in Path(path).parts,
                    "decoder_path_invalid")
        require(all(type(value) is str and _HEX.fullmatch(value)
                    for value in (self.ffmpeg_sha256, self.ffprobe_sha256)), "decoder_digest_invalid")

    @classmethod
    def read(cls, path):
        value = strict_json(Path(path).read_bytes())
        require(type(value) is dict and set(value) == {"record_type", "ffmpeg", "ffmpeg_sha256", "ffprobe", "ffprobe_sha256", "bwrap"}
                and value["record_type"] == "component_media_tools/v1", "decoder_configuration_invalid")
        return cls(**{key: value[key] for key in value if key != "record_type"})


def mp4_structure(data):
    """Refuse fragments, external references, unknown boxes and unbound bytes."""
    require(type(data) is bytes and 0 < len(data) <= MAX_FILE_BYTES, "media_file_size")
    box_count, tracks, codecs, offsets, sample_bytes, media_ranges = 0, 0, [], [], [], []
    text_metadata = []

    def boxes(start, end, depth):
        nonlocal box_count
        require(depth <= MAX_DEPTH, "mp4_box_depth")
        while start < end:
            box_count += 1
            require(box_count <= MAX_BOXES and end - start >= 8, "mp4_box_count_or_truncation")
            size, kind = struct.unpack_from(">I4s", data, start)
            header = 8
            if size == 1:
                require(end - start >= 16, "mp4_extended_size_truncated")
                size, = struct.unpack_from(">Q", data, start + 8)
                header = 16
            require(header <= size <= end - start, "mp4_box_size")
            yield kind, start + header, start + size
            start += size
        require(start == end, "mp4_trailing_bytes")

    def walk(kind, start, end, depth, metadata_key=None):
        nonlocal tracks
        if kind == b"trak":
            tracks += 1
            require(tracks <= 2, "mp4_track_count")
        if kind in _CONTAINERS:
            metadata_key = {b"\xa9too": "encoder", b"\xa9nam": "title"}.get(kind, metadata_key)
            if kind == b"meta":
                require(data[start:start + 4] == b"\0\0\0\0", "mp4_meta_version")
                start += 4
            children = list(boxes(start, end, depth + 1))
            require(bool(children), "mp4_empty_container")
            names = [child for child, _, _ in children if not (kind == b"moov" and child == b"trak")]
            require(len(names) == len(set(names)), "mp4_duplicate_box")
            for child, left, right in children:
                require(child in _CONTAINERS[kind], "mp4_box_unsupported")
                walk(child, left, right, depth + 1, metadata_key)
        elif kind == b"dref":
            require(end - start >= 8 and data[start:start + 4] == bytes(4), "mp4_data_reference_invalid")
            count, = struct.unpack_from(">I", data, start + 4)
            entries = list(boxes(start + 8, end, depth + 1))
            require(count == len(entries) == 1, "mp4_data_reference_count")
            child, left, right = entries[0]
            require(child == b"url " and data[left:right] == b"\0\0\0\1", "mp4_external_data_reference")
        elif kind == b"stsd":
            require(end - start >= 8 and data[start:start + 4] == bytes(4), "mp4_sample_description_invalid")
            count, = struct.unpack_from(">I", data, start + 4)
            entries = list(boxes(start + 8, end, depth + 1))
            require(count == len(entries) == 1, "mp4_sample_description_count")
            codec, left, right = entries[0]
            require(codec in (b"avc1", b"mp4a") and right - left >= 8
                    and data[left:left + 6] == bytes(6) and data[left + 6:left + 8] == b"\0\1", "mp4_codec_or_reference")
            codecs.append(codec)
            fixed = 78 if codec == b"avc1" else 28
            require(right - left >= fixed, "mp4_sample_entry_truncated")
            if codec == b"avc1":
                width, height = struct.unpack_from(">HH", data, left + 24)
                require(0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE and width * height <= MAX_PIXELS,
                        "media_dimensions")
            children = list(boxes(left + fixed, right, depth + 1))
            permitted = {b"avcC", b"pasp", b"btrt", b"colr"} if codec == b"avc1" else {b"esds", b"btrt"}
            require(all(child in permitted for child, _, _ in children), "mp4_codec_box_unsupported")
            require(sum(child == (b"avcC" if codec == b"avc1" else b"esds") for child, _, _ in children) == 1,
                    "mp4_codec_configuration_missing")
        elif kind in (b"stco", b"co64"):
            require(end - start >= 8 and data[start:start + 4] == bytes(4), "mp4_chunk_table_invalid")
            count, = struct.unpack_from(">I", data, start + 4)
            size = 4 if kind == b"stco" else 8
            require(0 < count <= MAX_SAMPLES and end - start == 8 + count * size, "mp4_chunk_table_size")
            offsets.extend(struct.unpack_from(">I" if size == 4 else ">Q", data, start + 8 + index * size)[0] for index in range(count))
        elif kind == b"stsz":
            require(end - start >= 12 and data[start:start + 4] == bytes(4), "mp4_sample_table_invalid")
            size, count = struct.unpack_from(">II", data, start + 4)
            require(0 < count <= MAX_SAMPLES and end - start == (12 if size else 12 + 4 * count), "mp4_sample_table_size")
            sample_bytes.append(size * count if size else sum(struct.unpack_from(">I", data, start + 12 + 4 * index)[0] for index in range(count)))
        elif kind == b"data":
            require(8 < end - start <= 520 and data[start:start + 8] == b"\0\0\0\1\0\0\0\0"
                    and metadata_key in ("encoder", "title"), "mp4_metadata_unsupported")
            payload = data[start + 8:end]
            if metadata_key == "encoder":
                require(re.fullmatch(rb"Lavf[0-9.]{1,32}", payload), "mp4_encoder_metadata_unsupported")
            try:
                text = payload.decode("utf-8")
            except UnicodeError:
                raise MediaValidationError("mp4_metadata_not_utf8") from None
            require(not any(unicodedata.category(char).startswith("C") for char in text), "mp4_metadata_controls")
            text_metadata.append(text)

    top = list(boxes(0, len(data), 0))
    require(top and top[0][0] == b"ftyp" and all(kind in (b"ftyp", b"moov", b"mdat", b"free") for kind, _, _ in top),
            "mp4_top_level_unsupported")
    require(all(sum(kind == expected for kind, _, _ in top) == 1 for expected in (b"ftyp", b"moov", b"mdat")),
            "mp4_required_box_count")
    for kind, start, end in top:
        if kind == b"ftyp":
            brands = {b"isom", b"iso2", b"mp41", b"mp42", b"avc1"}
            require(end - start >= 8 and (end - start) % 4 == 0 and data[start:start + 4] in brands
                    and all(data[pos:pos + 4] in brands for pos in range(start + 8, end, 4)), "mp4_brand_unsupported")
        elif kind == b"mdat":
            media_ranges.append((start, end))
        elif kind == b"free":
            require(end - start <= 4096 and not any(data[start:end]), "mp4_free_box_data")
        else:
            walk(kind, start, end, 0)
    require(codecs.count(b"avc1") == 1 and codecs.count(b"mp4a") <= 1 and len(codecs) == tracks,
            "mp4_stream_profile")
    require(offsets and all(any(start <= offset < end for start, end in media_ranges) for offset in offsets),
            "mp4_chunk_outside_media")
    require(len(sample_bytes) == tracks and sum(sample_bytes) == sum(end - start for start, end in media_ranges),
            "mp4_unbound_media_bytes")
    return {"boxes": box_count, "tracks": tracks, "codecs": [codec.decode() for codec in codecs],
            "text_metadata": text_metadata}


def manifest_binding(component, path):
    """Originals and derivatives must bind to exact files in this package."""
    require(component.line == "creative_originals", "media_supply_line_unsupported")
    value = strict_json(component.payloads.get(MANIFEST_NAME, b""))
    require(type(value) is dict and set(value) == {"record_type", "resources"}
            and value["record_type"] == MANIFEST_VERSION and type(value["resources"]) is list,
            "media_manifest_invalid")
    media_paths = {entry.path for entry in component.package.files if entry.media_type == "video/mp4"}
    rows = value["resources"]
    require(len(rows) == len(media_paths) and all(type(row) is dict and set(row) == {
        "path", "sha256", "role", "original", "source_files"} and type(row["path"]) is str
        for row in rows), "media_manifest_shape")
    require({row["path"] for row in rows} == media_paths, "media_manifest_coverage")
    require(path in media_paths, "media_path_not_in_package")
    def exact(binding):
        require(type(binding) is dict and set(binding) == {"path", "sha256"}
                and type(binding["path"]) is str and type(binding["sha256"]) is str
                and _HEX.fullmatch(binding["sha256"]), "media_binding_invalid")
        body = component.payloads.get(binding["path"])
        require(type(body) is bytes and hashlib.sha256(body).hexdigest() == binding["sha256"], "media_binding_mismatch")
    for row in rows:
        exact({"path": row["path"], "sha256": row["sha256"]})
        require(row["role"] in ("original", "derivative"), "media_role_invalid")
        if row["role"] == "original":
            require(row["original"] is None, "original_binding_must_be_null")
        else:
            exact(row["original"])
            require(row["original"]["path"] != row["path"] and any(other["path"] == row["original"]["path"]
                and other["role"] == "original" for other in rows), "original_resource_not_in_package")
        require(type(row["source_files"]) is list and 1 <= len(row["source_files"]) <= 32, "media_sources_required")
        for source in row["source_files"]:
            exact(source)
            require(source["path"] not in media_paths and source["path"] != MANIFEST_NAME, "media_source_not_render_source")
        require(len({item["path"] for item in row["source_files"]}) == len(row["source_files"]), "media_source_duplicate")
    return next(row for row in rows if row["path"] == path)


def sealed_bytes(data, name, mode=0o444):
    import fcntl
    require(hasattr(os, "memfd_create"), "sealed_file_unavailable")
    descriptor = os.memfd_create(name, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(data)
        os.fchmod(descriptor, mode)
        fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS,
                    fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def pinned_tool(path, expected):
    """Copy one stable regular executable into a sealed, digest-bound descriptor."""
    require(str(Path(path).resolve()) == path, "decoder_symlink_refused")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_mode & 0o111 and 0 < before.st_size <= MAX_TOOL_BYTES,
                "decoder_file_invalid")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            body = stream.read(MAX_TOOL_BYTES + 1)
        after = os.fstat(descriptor)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                and len(body) == before.st_size, "decoder_changed_during_read")
        require(hashlib.sha256(body).hexdigest() == expected, "decoder_digest_mismatch")
        return sealed_bytes(body, "qualified-media-decoder", 0o555)
    finally:
        os.close(descriptor)


def sandbox_command(settings, tool_fd, input_fd, arguments):
    return [settings.bwrap, "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
        "--cap-drop", "ALL", "--dir", "/decoder", "--dir", "/input",
        "--perms", "0555", "--ro-bind-data", str(tool_fd), "/decoder/program",
        "--perms", "0444", "--ro-bind-data", str(input_fd), "/input/media.mp4",
        "--proc", "/proc", "--dev", "/dev",
        "--size", str(TMP_BYTES), "--tmpfs", "/tmp", "--chdir", "/input", "--setenv", "LANG", "C",
        "--", "/decoder/program", *arguments]


def run_decoder(settings, tool, expected, data, arguments):
    """No fallback. Pipes, process time and resource use have independent bounds."""
    tool_fd = input_fd = None
    process = None
    try:
        tool_fd = pinned_tool(tool, expected)
        input_fd = sealed_bytes(data, "qualified-media-input")
        process = subprocess.Popen(sandbox_command(settings, tool_fd, input_fd, arguments), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={}, pass_fds=(tool_fd, input_fd),
            start_new_session=True, preexec_fn=_limits(LIMITS))
        deadline, buffers = time.monotonic() + WALL_SECONDS, {"stdout": bytearray(), "stderr": bytearray()}
        with selectors.DefaultSelector() as selector:
            for name in buffers:
                stream = getattr(process, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                require(remaining > 0, "decoder_timeout")
                for key, _mask in selector.select(min(0.1, remaining)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffers[key.data].extend(chunk)
                    require(sum(map(len, buffers.values())) <= MAX_OUTPUT_BYTES, "decoder_output_limit")
        remaining = deadline - time.monotonic()
        require(remaining > 0, "decoder_timeout")
        process.wait(timeout=remaining)
        require(process.returncode == 0, "decoder_refused")
        return {name: bytes(body) for name, body in buffers.items()}
    except subprocess.TimeoutExpired:
        raise MediaValidationError("decoder_timeout") from None
    except OSError:
        raise MediaValidationError("decoder_or_sandbox_unavailable") from None
    finally:
        if process is not None:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        for descriptor in (tool_fd, input_fd):
            if descriptor is not None:
                os.close(descriptor)


def metadata(value):
    require(type(value) is dict and type(value.get("streams")) is list and 1 <= len(value["streams"]) <= 2
            and all(type(stream) is dict for stream in value["streams"]) and type(value.get("format")) is dict,
            "media_stream_count")
    videos = [stream for stream in value["streams"] if stream.get("codec_type") == "video"]
    audio = [stream for stream in value["streams"] if stream.get("codec_type") == "audio"]
    require(len(videos) == 1 and len(audio) <= 1 and len(videos) + len(audio) == len(value["streams"]), "media_stream_type")
    video = videos[0]
    width, height = video.get("width"), video.get("height")
    require(type(width) is int and type(height) is int and 0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE
            and width * height <= MAX_PIXELS, "media_dimensions")
    require(video.get("codec_name") == "h264" and video.get("pix_fmt") == "yuv420p"
            and video.get("field_order") == "progressive" and type(video.get("disposition")) is dict
            and video["disposition"].get("attached_pic") == 0,
            "media_video_profile")
    try:
        duration = float(value["format"]["duration"])
        fps = Fraction(video["avg_frame_rate"])
        frames = int(video["nb_frames"])
    except (KeyError, ValueError, TypeError, ZeroDivisionError, OverflowError):
        raise MediaValidationError("media_timing_invalid") from None
    require(math.isfinite(duration) and 0 < duration <= MAX_SECONDS and 0 < fps <= MAX_FPS
            and 1 <= frames <= MAX_FRAMES and abs(float(frames / fps) - duration) <= 0.15,
            "media_timing_outside_profile")
    if audio:
        require(audio[0].get("codec_name") == "aac" and audio[0].get("profile") == "LC"
                and type(audio[0].get("channels")) is int
                and audio[0].get("channels") in (1, 2)
                and audio[0].get("sample_rate") in ("44100", "48000"), "media_audio_profile")
    return {"width": width, "height": height, "duration_seconds": duration, "frames": frames,
            "frame_rate": str(fps), "audio": bool(audio)}


def validate(data, settings):
    require(isinstance(settings, MediaTools), "media_decoder_not_configured")
    structure = mp4_structure(data)
    metadata_digest = hashlib.sha256(json.dumps(structure.pop("text_metadata")).encode()).hexdigest()
    common = ["-hide_banner", "-max_alloc", "67108864", "-threads", "1", "-protocol_whitelist", "file",
              "-format_whitelist", "mov", "-enable_drefs", "0", "-use_absolute_path", "0", "-err_detect", "explode"]
    probe = run_decoder(settings, settings.ffprobe, settings.ffprobe_sha256, data,
        ["-v", "error", *common, "-show_entries",
         "format=duration:stream=codec_type,codec_name,profile,width,height,pix_fmt,field_order,avg_frame_rate,nb_frames,channels,sample_rate:stream_disposition=attached_pic",
         "-of", "json", "/input/media.mp4"])
    facts = metadata(strict_json(probe["stdout"]))
    decoded = run_decoder(settings, settings.ffmpeg, settings.ffmpeg_sha256, data,
        ["-nostdin", "-v", "info", "-xerror", *common, "-i", "/input/media.mp4", "-map", "0:v:0", "-map", "0:a?",
         "-filter_threads", "1", "-vf", "showinfo", "-progress", "pipe:1", "-nostats", "-f", "null", "-"])
    frames = re.findall(rb"\bn:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:(\S+).*?\bfmt:(\S+).*?\bs:(\d+)x(\d+)\s", decoded["stderr"])
    require(len(frames) == facts["frames"], "decoded_frame_count_mismatch")
    previous = -1.0
    fps = Fraction(facts["frame_rate"])
    for index, (_number, _pts, clock, pixel_format, width, height) in enumerate(frames):
        try:
            seconds = float(clock)
        except ValueError:
            raise MediaValidationError("decoded_timing_invalid") from None
        require(int(_number) == index and int(width) == facts["width"] and int(height) == facts["height"]
                and pixel_format == b"yuv420p" and math.isfinite(seconds) and 0 <= seconds <= MAX_SECONDS
                and previous < seconds and abs(seconds - float(index / fps)) <= 0.001,
                "decoded_frame_profile_changed")
        previous = seconds
    require(decoded["stdout"].rstrip().endswith(b"progress=end"), "decode_completion_missing")
    return {"record_type": "component_media_decode/v1", "profile": PROFILE,
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), **facts, "structure": structure,
            "ffmpeg_sha256": settings.ffmpeg_sha256, "ffprobe_sha256": settings.ffprobe_sha256,
            "decode_complete": True, "sandbox": "sealed_inputs_bwrap_no_network_rlimits",
            "limits": {"maximum_file_bytes": MAX_FILE_BYTES, "maximum_seconds": MAX_SECONDS,
                       "maximum_frames": MAX_FRAMES, "maximum_pixels": MAX_PIXELS,
                       "decoder_output_bytes": MAX_OUTPUT_BYTES, "tmp_bytes": TMP_BYTES,
                       "cpu_soft_seconds": LIMITS.cpu_seconds, "cpu_hard_seconds": LIMITS.cpu_seconds + 5,
                       "wall_seconds": WALL_SECONDS, "address_space_bytes": LIMITS.memory_bytes,
                       "file_bytes": LIMITS.file_bytes, "open_files": LIMITS.open_files,
                       "core_bytes": 0, "cgroup_task_limit_enforced": False},
            "container_metadata_sha256": metadata_digest,
            "metadata_sha256": hashlib.sha256(probe["stdout"]).hexdigest()}
