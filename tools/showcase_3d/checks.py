"""Deterministic acceptance checks for the five 3D tasks.

Kind: evaluator for tools/showcase_3d. It needs numpy, trimesh, shapely and Pillow; the three.js check also needs
Node, playwright-core and a Chrome binary, named by the flags below.

Usage: python checks.py TASK_ID RUN_FOLDER --reference REFERENCE_FOLDER [--node NODE --playwright-core INDEX --chrome CHROME]
Prints one JSON record: {"task", "passed", "checks": [{"name", "passed", "detail"}], "reason"}.
A check that cannot run fails with its reason; nothing is skipped silently. Every reported name must be
defined in tasks.CHECK_DEFINITIONS.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tasks import ACCEPTANCE, CHECK_DEFINITIONS, TASKS  # noqa: E402


@dataclass(frozen=True)
class BrowserTools:
    """The programs the three.js check runs: Node, the playwright-core entry module and a Chrome binary."""
    node: str
    playwright_core: str
    chrome: str


class UndefinedCheck(Exception):
    """A reported check name has no written definition: a defect of the checker, never a failed check."""


class Result:
    def __init__(self, task):
        self.task, self.checks = task, []
        self.defined = {name for name, _ in CHECK_DEFINITIONS[task]}

    def add(self, name, passed, detail=""):
        if name not in self.defined:
            raise UndefinedCheck(f"check {name} has no written definition for {self.task}")
        self.checks.append({"name": name, "passed": bool(passed), "detail": str(detail)[:300]})
        return bool(passed)

    def record(self):
        failed = [c for c in self.checks if not c["passed"]]
        return {"task": self.task, "passed": bool(self.checks) and not failed, "checks": self.checks,
                "reason": failed[0]["name"] + ": " + failed[0]["detail"] if failed else "all checks passed"}


def merged(mesh):
    import numpy as np
    import trimesh
    clean = trimesh.Trimesh(vertices=np.asarray(mesh.vertices), faces=np.asarray(mesh.faces), process=False)
    clean.merge_vertices(merge_tex=True, merge_norm=True)
    return clean


def load_mesh(path: Path):
    import trimesh
    return merged(trimesh.load(str(path), force="mesh", process=True))


def solid_checks(result: Result, mesh) -> bool:
    ok = result.add("watertight", mesh.is_watertight, f"faces={len(mesh.faces)}")
    ok &= result.add("winding_consistent", mesh.is_winding_consistent, "")
    ok &= result.add("positive_volume", mesh.is_watertight and mesh.volume > 0,
                     f"volume={mesh.volume:.2f}" if mesh.is_watertight else "not watertight")
    bodies = mesh.split(only_watertight=False)
    ok &= result.add("single_body", len(bodies) == 1, f"bodies={len(bodies)}")
    return ok


def check_gear(result: Result, folder: Path) -> None:
    import numpy as np
    import shapely.geometry as sg
    spec = ACCEPTANCE["t1_gear"]
    mesh = load_mesh(folder / "gear.stl")
    solid_checks(result, mesh)
    lo, hi = mesh.bounds
    result.add("thickness", abs((hi[2] - lo[2]) - spec["thickness"]) <= spec["thickness_tol"], f"z extent={hi[2]-lo[2]:.3f}")
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    radii = np.hypot(mesh.vertices[:, 0] - cx, mesh.vertices[:, 1] - cy)
    result.add("outer_diameter", abs(2 * radii.max() - spec["outer_diameter"]) <= spec["outer_tol"], f"outer={2*radii.max():.3f}")
    middle = [cx, cy, (lo[2] + hi[2]) / 2]
    section = mesh.section(plane_origin=middle, plane_normal=[0, 0, 1])
    if section is None:
        result.add("mid_section", False, "no section at mid height"); return
    planar, to_3d = section.to_2D()
    polygons = planar.polygons_full
    if not polygons:
        result.add("mid_section", False, "section has no closed polygon"); return
    polygon = max(polygons, key=lambda p: p.area)
    c2 = (np.linalg.inv(to_3d) @ np.array(middle + [1.0]))[:2]
    ring = np.asarray(polygon.exterior.coords)
    dense = [ring[0]]
    for a, b in zip(ring[:-1], ring[1:]):
        steps = max(1, int(np.linalg.norm(b - a) / 0.05))
        dense.extend(a + (b - a) * t for t in np.linspace(0, 1, steps + 1)[1:])
    dense = np.asarray(dense) - c2
    angle = np.arctan2(dense[:, 1], dense[:, 0]); radius = np.hypot(dense[:, 0], dense[:, 1])
    bins = 3600
    index = ((angle + math.pi) / (2 * math.pi) * bins).astype(int) % bins
    profile = np.full(bins, np.nan)
    for i, r in zip(index, radius):
        if np.isnan(profile[i]) or r > profile[i]:
            profile[i] = r
    valid = ~np.isnan(profile)
    profile = np.interp(np.arange(bins), np.arange(bins)[valid], profile[valid], period=bins)
    depth = profile.max() - profile.min()
    result.add("tooth_depth", depth >= spec["min_tooth_depth"], f"depth={depth:.3f}")
    threshold = (profile.max() + profile.min()) / 2
    above = profile > threshold
    teeth = int(np.sum(above & ~np.roll(above, 1)))
    result.add("tooth_count", teeth == spec["teeth"], f"teeth={teeth}")
    shape = sg.MultiPolygon(polygons) if len(polygons) > 1 else polygons[0]
    angles = np.linspace(0, 2 * np.pi, 7200, endpoint=False)
    inside = [shape.contains(sg.Point(c2[0] + spec["pitch_radius"] * np.cos(a), c2[1] + spec["pitch_radius"] * np.sin(a)))
              for a in angles]
    share = float(np.mean(inside))
    result.add("tooth_thickness", spec["tooth_share_min"] <= share <= spec["tooth_share_max"],
               f"pitch circle share in material={share:.3f}")
    holes = list(polygon.interiors)
    diameters = [2 * math.sqrt(abs(sg.Polygon(h).area) / math.pi) for h in holes]
    offsets = [float(np.linalg.norm(np.asarray(sg.Polygon(h).centroid.coords[0]) - c2)) for h in holes]
    result.add("bore", len(holes) == 1 and abs(diameters[0] - spec["bore"]) <= spec["bore_tol"] and offsets[0] <= 0.5,
               f"holes={len(holes)} diameters={[round(d, 3) for d in diameters]} offsets={[round(o, 3) for o in offsets]}")


def check_stand(result: Result, folder: Path) -> None:
    import numpy as np
    spec = ACCEPTANCE["t2_stand"]
    mesh = load_mesh(folder / "stand.stl")
    solid_checks(result, mesh)
    lo, hi = mesh.bounds
    ext = hi - lo
    result.add("footprint_x", abs(ext[0] - spec["x"]) <= spec["xy_tol"], f"x={ext[0]:.3f}")
    result.add("footprint_y", abs(ext[1] - spec["y"]) <= spec["xy_tol"], f"y={ext[1]:.3f}")
    result.add("on_z0", abs(lo[2]) <= spec["base_z_tol"], f"z_min={lo[2]:.4f}")
    result.add("height", hi[2] <= spec["max_z"] + 1e-6, f"z_max={hi[2]:.3f}")
    normals, areas = mesh.face_normals, mesh.area_faces
    low = np.all(mesh.vertices[mesh.faces][:, :, 2] <= lo[2] + spec["base_z_tol"], axis=1)
    base_area = float(areas[(normals[:, 2] <= -0.999) & low].sum())
    result.add("flat_base", base_area >= spec["min_base_fraction"] * spec["x"] * spec["y"], f"base area={base_area:.1f}")
    theta = math.radians(spec["angle_deg"])
    target = np.array([0.0, -math.sin(theta), math.cos(theta)])
    aligned = normals @ target >= math.cos(math.radians(spec["angle_tol_deg"]))
    patch = 0.0
    if aligned.any():
        sub = mesh.submesh([np.nonzero(aligned)[0]], append=True)
        patch = max(float(part.area) for part in sub.split(only_watertight=False)) if len(sub.faces) else 0.0
    result.add("support_face", patch >= spec["min_support_area"],
               f"largest aligned patch={patch:.1f} total aligned={float(areas[aligned].sum()):.1f}")


def check_house(result: Result, folder: Path) -> None:
    import numpy as np
    import trimesh
    spec = ACCEPTANCE["t3_house"]
    path = folder / "house.glb"
    head = path.read_bytes()[:12]
    result.add("glb_header", head[:4] == b"glTF" and int.from_bytes(head[4:8], "little") == 2, repr(head[:8]))
    scene = trimesh.load(str(path), force="scene", process=False)
    groups = {"walls": [], "roof": []}
    triangles = 0
    for node in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph[node]
        geometry = scene.geometry[geometry_name]
        if not hasattr(geometry, "faces"):
            continue
        triangles += len(geometry.faces)
        label = (str(node) + " " + str(geometry_name)).lower()
        for key in groups:
            if key.rstrip("s") in label:
                groups[key].append(geometry.copy().apply_transform(transform))
    result.add("triangle_budget", triangles <= spec["max_triangles"], f"triangles={triangles}")
    result.add("named_walls_and_roof", all(groups.values()), f"walls={len(groups['walls'])} roof={len(groups['roof'])}")
    if not all(groups.values()):
        return
    walls = merged(trimesh.util.concatenate(groups["walls"]))
    roof = merged(trimesh.util.concatenate(groups["roof"]))
    w, r = spec["walls"], spec["roof"]
    (wx0, wy0, wz0), (wx1, wy1, wz1) = walls.bounds
    result.add("walls_watertight", walls.is_watertight, f"faces={len(walls.faces)}")
    result.add("walls_size", abs((wx1 - wx0) - w["x"]) <= w["tol"] and abs((wz1 - wz0) - w["z"]) <= w["tol"]
               and abs(wy0 - w["y0"]) <= w["tol"] and abs(wy1 - w["y1"]) <= w["tol"],
               f"x={wx1-wx0:.3f} z={wz1-wz0:.3f} y={wy0:.3f}..{wy1:.3f}")
    (rx0, ry0, rz0), (rx1, ry1, rz1) = roof.bounds
    result.add("roof_watertight", roof.is_watertight, f"faces={len(roof.faces)}")
    result.add("roof_heights", abs(ry0 - r["y0"]) <= r["tol_low"] and abs(ry1 - r["y1"]) <= r["tol_ridge"], f"y={ry0:.3f}..{ry1:.3f}")
    result.add("roof_covers_walls", (rx1 - rx0) >= r["min_x"] - 0.01 and (rz1 - rz0) >= r["min_z"] - 0.01
               and rx0 <= wx0 + 0.01 and rx1 >= wx1 - 0.01 and rz0 <= wz0 + 0.01 and rz1 >= wz1 - 0.01,
               f"roof x={rx0:.2f}..{rx1:.2f} z={rz0:.2f}..{rz1:.2f}")
    top = roof.vertices[roof.vertices[:, 1] >= ry1 - 0.05]
    span_x = float(np.ptp(top[:, 0])) if len(top) else 0.0
    span_z = float(np.ptp(top[:, 2])) if len(top) else 99.0
    result.add("ridge_along_x", span_x >= w["x"] - 0.1 and span_z <= 0.1, f"ridge span x={span_x:.3f} z={span_z:.3f}")


def check_threejs(result: Result, folder: Path, tools: BrowserTools | None) -> None:
    import numpy as np
    from PIL import Image
    spec = ACCEPTANCE["t4_threejs"]
    shot, report = folder / "_checker_screenshot.png", folder / "_checker_render.json"
    for stale in (shot, report):
        if stale.exists():
            stale.unlink()
    if tools is None:
        result.add("render_harness", False, "the checker was not given --node, --playwright-core and --chrome")
        return
    command = [tools.node, str(HERE / "render_check.mjs"), str(folder), str(shot), str(report),
               str(spec["render_timeout_ms"]), tools.playwright_core, tools.chrome]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if not report.exists():
        result.add("render_harness", False, (completed.stderr or completed.stdout)[-300:]); return
    data = json.loads(report.read_text())
    if data.get("checker_errors"):
        result.add("render_harness", False, "; ".join(data["checker_errors"])[:300]); return
    result.add("rendered_flag", data.get("rendered") is True, f"rendered={data.get('rendered')}")
    errors = data.get("console_errors", []) + data.get("page_errors", [])
    result.add("no_console_errors", not errors, "; ".join(errors)[:300])
    result.add("no_external_requests", not data.get("blocked_requests"), "; ".join(data.get("blocked_requests", []))[:300])
    result.add("canvas_fills_window", data.get("canvas_fraction", 0) >= spec["min_canvas_fraction"], f"canvas fraction={data.get('canvas_fraction')}")
    if not shot.exists():
        result.add("screenshot", False, "no screenshot"); return
    pixels = np.asarray(Image.open(shot).convert("RGB")).astype(int).reshape(-1, 3)
    r, g, b = pixels[:, 0], pixels[:, 1], pixels[:, 2]
    red = np.mean((r > 60) & (r > 1.8 * g) & (r > 1.8 * b))
    blue = np.mean((b > 60) & (b > 1.5 * r) & (b > 1.3 * g))
    grey = np.mean((np.abs(r - g) < 14) & (np.abs(g - b) < 14) & (r > 110))
    result.add("red_cube_visible", red >= spec["min_red_fraction"], f"red fraction={red:.4f}")
    result.add("blue_sphere_visible", blue >= spec["min_blue_fraction"], f"blue fraction={blue:.4f}")
    result.add("grey_ground_visible", grey >= spec["min_grey_fraction"], f"grey fraction={grey:.4f}")


def check_repair(result: Result, folder: Path, reference: Path) -> None:
    import numpy as np
    import trimesh
    spec = ACCEPTANCE["t5_repair"]
    mesh = load_mesh(folder / "repaired.stl")
    truth = load_mesh(reference / "bracket_reference.stl")
    if not solid_checks(result, mesh):
        return
    result.add("volume_matches", abs(mesh.volume - truth.volume) <= spec["volume_tol"] * truth.volume,
               f"volume={mesh.volume:.2f} reference={truth.volume:.2f}")
    result.add("size_matches", bool(np.all(np.abs(mesh.extents - truth.extents) <= spec["extent_tol_mm"])),
               f"extents={np.round(mesh.extents, 3).tolist()} reference={np.round(truth.extents, 3).tolist()}")
    offset = mesh.bounds[0] - truth.bounds[0]
    samples, _ = trimesh.sample.sample_surface(mesh, 3000, seed=7)
    _, distance, _ = trimesh.proximity.closest_point(truth, samples - offset)
    back, _ = trimesh.sample.sample_surface(truth, 3000, seed=11)
    _, distance_back, _ = trimesh.proximity.closest_point(mesh, back + offset)
    p99 = float(max(np.percentile(distance, 99), np.percentile(distance_back, 99)))
    result.add("shape_matches", p99 <= spec["p99_surface_distance_mm"], f"p99 surface distance={p99:.4f} mm")


def check(task: str, folder: Path, reference: Path, tools: BrowserTools | None = None) -> dict:
    result = Result(task)
    output = folder / TASKS[task]["output"]
    if not output.exists():
        result.add("output_exists", False, f"{output.name} missing")
        return result.record()
    result.add("output_exists", True, f"{output.stat().st_size} bytes")
    try:
        {"t1_gear": lambda: check_gear(result, folder), "t2_stand": lambda: check_stand(result, folder),
         "t3_house": lambda: check_house(result, folder), "t4_threejs": lambda: check_threejs(result, folder, tools),
         "t5_repair": lambda: check_repair(result, folder, reference)}[task]()
    except UndefinedCheck:
        raise
    except Exception as exc:  # a crash is a failed check, with its reason
        result.add("checker_ran", False, type(exc).__name__ + ": " + str(exc))
    return result.record()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=tuple(TASKS))
    parser.add_argument("folder", type=Path)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--node")
    parser.add_argument("--playwright-core")
    parser.add_argument("--chrome")
    args = parser.parse_args(argv)
    tools = BrowserTools(args.node, args.playwright_core, args.chrome) if args.node and args.playwright_core and args.chrome else None
    print(json.dumps(check(args.task, args.folder.resolve(), args.reference.resolve(), tools)))


if __name__ == "__main__":
    main()
