"""The five 3D tasks, their acceptance numbers and the written definition of every check.

Kind: evaluation data for the 3D with-and-without comparison (tools/showcase_3d/rerun.py).

The task text and the acceptance numbers are the ones the first comparison of September 27, 2026 used.
Additions after that comparison, made before any rerun: the gear check `tooth_thickness` (a gear with
needle-thin teeth passed the first checker), the Baltor note for the condition with material placed in
the harness, and a written definition for every check so that each can be recorded with a digest before
the first run.
"""
from __future__ import annotations

import hashlib
import json

COMMON = (
    "You are working in the current folder. Python 3.12 is available as `python` with numpy, trimesh, "
    "manifold3d, scipy, shapely, cadquery and build123d installed. Do not install packages. Work only in "
    "this folder and finish with the required file saved in it. Units are millimetres unless the task says otherwise.\n\n"
)

#: The only prompt difference between the two conditions. It names where the placed material is and
#: nothing about its content.
BALTOR_NOTE = (
    "Components from Baltor, a library of reusable harness components, are installed in this project as "
    "skills under .opencode/skills. Use them where they help.\n\n"
)

CONDITIONS = ("without_baltor", "with_baltor")

TASKS = {
    "t1_gear": {
        "output": "gear.stl",
        "supplied": [],
        "prompt": (
            "Task: create `gear.stl`, a spur gear for 3D printing. Requirements: exactly 24 teeth; module 2 mm, so the "
            "pitch diameter is 48 mm and the outer (tip) diameter is 52 mm (within 0.5 mm); thickness 8 mm along the Z "
            "axis; a round through-hole (bore) of 8 mm diameter at the centre; the gear axis is the Z axis. The mesh must "
            "be a single watertight solid."
        ),
    },
    "t2_stand": {
        "output": "stand.stl",
        "supplied": [],
        "prompt": (
            "Task: create `stand.stl`, a desk stand that holds a phone at an angle. Requirements: a single watertight "
            "solid; it sits on the plane z = 0 with a flat bottom; its footprint is 80 mm along X and 70 mm along Y (each "
            "within 1 mm); its height is at most 90 mm. It has one flat support surface for the back of the phone, at "
            "least 60 mm long along its slope and at least 40 mm wide, inclined at 65 degrees from horizontal (within 2 "
            "degrees), facing up and toward the -Y side (the front)."
        ),
    },
    "t3_house": {
        "output": "house.glb",
        "supplied": [],
        "prompt": (
            "Task: create `house.glb`, a low-poly house as a binary glTF 2.0 file. glTF uses Y as the up axis and metres "
            "as units. Requirements: two separate meshes in two separate nodes, named `walls` and `roof`. The walls are "
            "a closed box 6 m along X, 4 m along Z and 3 m tall, standing on y = 0. The roof is a closed gable roof (a "
            "triangular prism) whose lowest edges are at y = 3 and whose ridge is at y = 4.5, running along X, and it "
            "covers the walls (at least 6 m along X and at least 4 m along Z). The whole file has at most 500 triangles."
        ),
    },
    "t4_threejs": {
        "output": "index.html",
        "supplied": ["vendor/three.module.min.js", "vendor/three.core.min.js", "vendor/LICENSE"],
        "prompt": (
            "Task: create `index.html` that renders a 3D scene with three.js in a web browser. Use the three.js module "
            "already in this folder, `./vendor/three.module.min.js` (it imports `./vendor/three.core.min.js` itself); "
            "load nothing from the internet. The scene: a red cube and a blue sphere side by side, standing on a light "
            "grey ground plane, lit by at least one directional light, seen by a perspective camera that shows both "
            "objects. The canvas fills the whole window. After the first frame has been rendered, the page sets "
            "`window.__rendered = true`. The page must cause no errors in the browser console."
        ),
    },
    "t5_repair": {
        "output": "repaired.stl",
        "supplied": ["broken.stl"],
        "prompt": (
            "Task: `broken.stl` in this folder is a mechanical bracket whose mesh is damaged: it has holes where "
            "triangles are missing, some triangles have flipped orientation, and some triangles are duplicated. "
            "Create `repaired.stl`: the same part as a single watertight solid with consistently "
            "outward-facing triangles. Do not change the part's shape or size: close the holes; do not replace the part "
            "with a convex hull, a box or a remeshed approximation."
        ),
    },
}

ACCEPTANCE = {
    "t1_gear": {"teeth": 24, "outer_diameter": 52.0, "outer_tol": 0.5, "thickness": 8.0, "thickness_tol": 0.2,
                "bore": 8.0, "bore_tol": 0.4, "min_tooth_depth": 1.5,
                "pitch_radius": 24.0, "tooth_share_min": 0.30, "tooth_share_max": 0.70},
    "t2_stand": {"x": 80.0, "y": 70.0, "xy_tol": 1.0, "max_z": 90.0, "base_z_tol": 0.05, "min_base_fraction": 0.25,
                 "angle_deg": 65.0, "angle_tol_deg": 2.0, "min_support_area": 2400.0},
    "t3_house": {"walls": {"x": 6.0, "z": 4.0, "y0": 0.0, "y1": 3.0, "tol": 0.05},
                 "roof": {"y0": 3.0, "y1": 4.5, "tol_low": 0.05, "tol_ridge": 0.1, "min_x": 6.0, "min_z": 4.0},
                 "max_triangles": 500},
    "t4_threejs": {"min_red_fraction": 0.003, "min_blue_fraction": 0.003, "min_grey_fraction": 0.05,
                   "min_canvas_fraction": 0.9, "render_timeout_ms": 30000},
    "t5_repair": {"volume_tol": 0.02, "extent_tol_mm": 0.3, "p99_surface_distance_mm": 0.5},
}

_SOLID = [
    ("watertight", "After duplicate vertices are merged, every edge of the mesh is shared by exactly two faces."),
    ("winding_consistent", "Neighbouring faces are oriented consistently."),
    ("positive_volume", "The mesh is watertight and its signed volume is positive, so its faces point outward."),
    ("single_body", "The mesh is one connected body."),
]
_ANY = [
    ("output_exists", "The required output file exists in the run folder."),
    ("checker_ran", "The checker finished without an exception; it appears only when the checker failed."),
]

#: Every check name the checker can report, with its definition in plain words. The checker refuses to
#: report a name that is not here.
CHECK_DEFINITIONS = {
    "t1_gear": _ANY + _SOLID + [
        ("thickness", "The Z extent is 8 mm within 0.2 mm."),
        ("outer_diameter", "Twice the largest vertex distance from the Z axis through the bounding-box centre is 52 mm within 0.5 mm."),
        ("mid_section", "A section at mid height gives at least one closed outline; it appears only when it does not."),
        ("tooth_depth", "In the mid-height section the outer radius varies by at least 1.5 mm around the axis."),
        ("tooth_count", "The outer radius rises above the midpoint between its smallest and largest value exactly 24 times around the axis."),
        ("tooth_thickness", "Between 30 and 70 percent of the pitch circle (radius 24 mm) lies inside material at mid height. Added after September 27, 2026."),
        ("bore", "The mid-height section has exactly one hole, of equivalent diameter 8 mm within 0.4 mm, centred within 0.5 mm of the axis."),
    ],
    "t2_stand": _ANY + _SOLID + [
        ("footprint_x", "The X extent is 80 mm within 1 mm."),
        ("footprint_y", "The Y extent is 70 mm within 1 mm."),
        ("on_z0", "The lowest point is at z = 0 within 0.05 mm."),
        ("height", "The highest point is at most 90 mm."),
        ("flat_base", "Downward faces at the lowest level cover at least a quarter of the 80 by 70 mm footprint."),
        ("support_face", "The largest connected patch of faces whose normals are within 2 degrees of a face inclined 65 degrees from horizontal, facing up and toward -Y, has at least 2,400 square millimetres."),
    ],
    "t3_house": _ANY + [
        ("glb_header", "The file starts with the binary glTF magic word and version 2."),
        ("triangle_budget", "The scene holds at most 500 triangles."),
        ("named_walls_and_roof", "At least one node or mesh is named for the walls and another for the roof."),
        ("walls_watertight", "The walls mesh is watertight."),
        ("walls_size", "The walls span 6 m in X and 4 m in Z and run from y = 0 to y = 3, each within 0.05 m."),
        ("roof_watertight", "The roof mesh is watertight."),
        ("roof_heights", "The roof runs from y = 3 within 0.05 m to y = 4.5 within 0.1 m."),
        ("roof_covers_walls", "The roof's X and Z extents cover the walls' extents."),
        ("ridge_along_x", "Roof vertices within 0.05 m of the top span at least 5.9 m in X and at most 0.1 m in Z."),
    ],
    "t4_threejs": _ANY + [
        ("render_harness", "The headless browser check finished, with its screenshot taken within three attempts; it appears only when it did not, and marks a checker fault, not the page's."),
        ("rendered_flag", "window.__rendered becomes true within 30 seconds, with the folder served locally."),
        ("no_console_errors", "The page logs no console error and throws no page error."),
        ("no_external_requests", "The page requests nothing outside the local server."),
        ("canvas_fills_window", "The canvas covers at least 90 percent of the window."),
        ("screenshot", "A screenshot was taken; it appears only when none was."),
        ("red_cube_visible", "At least 0.3 percent of the screenshot's pixels are red."),
        ("blue_sphere_visible", "At least 0.3 percent of the screenshot's pixels are blue."),
        ("grey_ground_visible", "At least 5 percent of the screenshot's pixels are light grey."),
    ],
    "t5_repair": _ANY + _SOLID + [
        ("volume_matches", "The volume is within 2 percent of the hidden reference bracket."),
        ("size_matches", "The bounding-box extents are within 0.3 mm of the reference."),
        ("shape_matches", "With the minimum corners aligned, the 99th percentile of surface distances in both directions is at most 0.5 mm."),
    ],
}


def prompt_for(task_id: str, condition: str) -> str:
    """The exact prompt of one run. The conditions differ only by BALTOR_NOTE."""
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition}")
    base = COMMON + TASKS[task_id]["prompt"]
    return (BALTOR_NOTE + base) if condition == "with_baltor" else base


def check_definition_records() -> list[dict]:
    """One record per check, each with the digest of its task, name, definition and the task's numbers."""
    records = []
    for task, rows in CHECK_DEFINITIONS.items():
        for name, words in rows:
            body = {"task": task, "check": name, "definition": words, "acceptance": ACCEPTANCE[task]}
            digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            records.append({**body, "digest": digest})
    return records
