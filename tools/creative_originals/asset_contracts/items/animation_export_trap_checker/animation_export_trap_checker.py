"""Animation export trap checker: the clips a scene declares against the clips its glTF export carries.

    python3 animation_export_trap_checker.py EXPORT.gltf --declared DECLARATION.json

An exporter can write a model with every mesh in place and quietly leave out its animation: only the active action
is exported, clips are merged into one, a channel loses its target node, or a clip is baked to a single pose. This
tool compares the export with a declaration of the clips the source scene holds (animation_declaration/v1, written
by procedure/declare_clips_blender.py, or the clips of an asset_specification/v1) and reports every declared clip
that is missing, merged, static, too short or too long, or missing one of its targets, and every channel whose target
cannot be resolved. Prints one JSON report; exits 0 when the export carries every declared clip, 1 otherwise.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import asset_report
import gltfio

TOOL = "animation_export_trap_checker"
DEFAULT_TOLERANCE_S = 0.05
MOTION_EPSILON = 1e-5
PATHS = ("translation", "rotation", "scale", "weights")
FAILURES = ("asset_unreadable", "declaration_invalid", "animations_missing", "clip_missing", "clips_merged",
            "clip_target_missing", "channel_target_unresolved", "clip_static", "clip_duration_mismatch")


def read_declaration(value, report: asset_report.Report) -> "list | None":
    """Declared clips as [{name, duration_s or None, tolerance_s, targets: [(node, path)]}]."""
    if not isinstance(value, dict) or value.get("record_type") not in ("animation_declaration/v1",
                                                                       "asset_specification/v1"):
        report.fail("declaration_invalid", "record_type", "animation_declaration/v1 or asset_specification/v1")
        return None
    clips = value.get("clips")
    if not isinstance(clips, list):
        report.fail("declaration_invalid", "clips", "a list of clips")
        return None
    declared = []
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict) or not isinstance(clip.get("name"), str) or not clip["name"]:
            report.fail("declaration_invalid", f"clips[{index}]", "each clip has a name")
            return None
        targets = []
        for target in clip.get("targets", []):
            node = target.get("node", target.get("part")) if isinstance(target, dict) else None
            if not isinstance(node, str) or target.get("path") not in PATHS:
                report.fail("declaration_invalid", f"clips[{index}].targets", f"node (or part) and a path in {PATHS}")
                return None
            targets.append((node, target["path"]))
        duration = clip.get("duration_s")
        if duration is not None and (type(duration) not in (int, float) or duration < 0):
            report.fail("declaration_invalid", f"clips[{index}].duration_s", repr(duration))
            return None
        declared.append({"name": clip["name"], "duration_s": duration, "targets": targets,
                         "tolerance_s": clip.get("tolerance_s", DEFAULT_TOLERANCE_S)})
    return declared


def export_clips(asset: gltfio.Asset) -> list:
    """Each exported clip: name, play length, and per channel the target node name, path, key count and motion.

    ``length_s`` and motion count resolved channels only, because an engine cannot play a channel without a target;
    ``length_all_channels_s`` includes the unresolved ones."""
    nodes, reachable = asset.items("nodes"), set(gltfio.world_matrices(asset.document))
    clips = []
    for index, animation in enumerate(asset.items("animations")):
        samplers, channels, end, end_all = animation.get("samplers", []), [], 0.0, 0.0
        for channel in animation.get("channels", []):
            target = channel.get("target", {}) if isinstance(channel, dict) else {}
            node = target.get("node")
            resolved = type(node) is int and 0 <= node < len(nodes) and node in reachable
            row = {"node": node, "node_name": nodes[node].get("name") if resolved else None,
                   "path": target.get("path"), "resolved": resolved, "keys": 0, "moving": False}
            sampler = channel.get("sampler")
            if type(sampler) is int and 0 <= sampler < len(samplers):
                try:
                    times = gltfio.accessor_values(asset, samplers[sampler].get("input"))
                    values = gltfio.accessor_values(asset, samplers[sampler].get("output"))
                except gltfio.GltfError:
                    times, values = [], []
                row["keys"] = len(times)
                end_all = max([end_all] + [time[0] for time in times])
                if resolved:
                    end = max([end] + [time[0] for time in times])
                if samplers[sampler].get("interpolation") == "CUBICSPLINE":
                    values = values[1::3]
                row["moving"] = any(max(abs(a - b) for a, b in zip(value, values[0])) > MOTION_EPSILON
                                    for value in values[1:])
            channels.append(row)
        clips.append({"index": index, "name": animation.get("name") or f"animation_{index}", "length_s": end,
                      "length_all_channels_s": end_all, "channels": channels})
    return clips


def compare(declared: list, clips: list, report: asset_report.Report) -> None:
    by_name = {clip["name"]: clip for clip in clips}
    if declared and not clips:
        report.fail("animations_missing", "animations", f"{len(declared)} clips declared, the export has none")
    missing = []
    for clip in declared:
        found = by_name.get(clip["name"])
        if found is None:
            variants = [name for name in by_name if clip["name"] in name]
            report.fail("clip_missing", clip["name"], "not in the export" + (
                f"; similar clip names {variants}" if variants else f"; export clips {sorted(by_name)}"))
            missing.append(clip)
            continue
        carried = {(channel["node_name"], channel["path"]) for channel in found["channels"] if channel["resolved"]}
        for node, path in clip["targets"]:
            if (node, path) not in carried:
                report.fail("clip_target_missing", clip["name"], f"no channel animates {node} {path}")
        if not carried:
            continue  # no playable channel: the target and unresolved channel failures already say why
        if not any(channel["moving"] for channel in found["channels"] if channel["resolved"]):
            report.fail("clip_static", clip["name"], "every channel holds one value: the clip plays but nothing moves")
        if clip["duration_s"] is not None and abs(found["length_s"] - clip["duration_s"]) > clip["tolerance_s"]:
            report.fail("clip_duration_mismatch", clip["name"], f"declared {clip['duration_s']} s, export plays "
                                                                f"{round(found['length_s'], 4)} s")
    declared_names = {clip["name"] for clip in declared}
    for clip in clips:
        if clip["name"] in declared_names:
            continue
        carried = {(channel["node_name"], channel["path"]) for channel in clip["channels"] if channel["resolved"]}
        covered = [item["name"] for item in missing if item["targets"] and set(item["targets"]) <= carried]
        if len(covered) >= 2:
            report.fail("clips_merged", clip["name"], f"one export clip carries the targets of declared clips {covered}")
    for clip in clips:
        for position, channel in enumerate(clip["channels"]):
            if not channel["resolved"]:
                report.fail("channel_target_unresolved", f"{clip['name']} channel {position}",
                            f"target node {channel['node']!r} is missing or outside the scene")


def check(asset_path, declaration_path) -> asset_report.Report:
    report = asset_report.Report(TOOL, Path(asset_path).name)
    try:
        asset = gltfio.load(asset_path)
        clips = export_clips(asset)
    except gltfio.GltfError as error:
        report.fail("asset_unreadable", Path(asset_path).name, f"{error.reason} {error.detail}")
        return report
    report.facts = {"export_clips": clips}
    value = asset_report.read_json_file(declaration_path, report, "declaration_invalid")
    declared = read_declaration(value, report) if value is not None else None
    if declared is None:
        return report
    report.facts["declared_clips"] = [clip["name"] for clip in declared]
    compare(declared, clips, report)
    return report


def run(argv: list) -> dict:
    parser = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n\n")[0])
    parser.add_argument("asset", help="the exported .gltf or .glb")
    parser.add_argument("--declared", required=True, help="animation_declaration/v1 or asset_specification/v1 JSON")
    arguments = parser.parse_args(argv)
    return check(arguments.asset, arguments.declared).as_dict()


def main(argv=None) -> int:
    return asset_report.emit(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
