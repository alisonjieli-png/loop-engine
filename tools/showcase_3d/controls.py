"""Build the supplied inputs, the hidden reference and the checker controls; run the checker on each.

Kind: evaluator controls for tools/showcase_3d. Every task has correct outputs that must pass and known-wrong
outputs that must fail on a named check. The first comparison of September 27, 2026 used the controls marked
`first`; the others were added before the rerun. Extra controls from real earlier outputs can be supplied
with --extra, a JSON list of {"task", "control", "folder", "expected_pass", "expected_failing_check"}.

Usage: python controls.py REFERENCE_FOLDER CONTROL_FOLDER REPORT.json --three THREE_PACKAGE_FOLDER
       --node NODE --playwright-core INDEX --chrome CHROME [--extra FILE]
The exit status is zero only when every control behaves as expected.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def gear_mesh(teeth=24, module=2.0, thickness=8.0, bore=8.0, flank=(0.18, 0.32, 0.68, 0.82)):
    import numpy as np
    import shapely.geometry as sg
    import trimesh
    tip, root = module * teeth / 2 + module, module * teeth / 2 - 1.25 * module
    rise, top, fall, bottom = flank
    points = []
    for i in range(teeth):
        base, step = 2 * math.pi * i / teeth, 2 * math.pi / teeth
        for fraction, radius in ((0.0, root), (rise, root), (top, tip), (fall, tip), (bottom, root)):
            angle = base + fraction * step
            points.append((radius * math.cos(angle), radius * math.sin(angle)))
    hole = [(bore / 2 * math.cos(a), bore / 2 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 64, endpoint=False)]
    return trimesh.creation.extrude_polygon(sg.Polygon(points, [hole]), thickness)


def stand_mesh(angle=65.0, width=80.0, depth=70.0, shift_z=0.0):
    import numpy as np
    import shapely.geometry as sg
    import trimesh
    a = math.radians(angle)
    d, u = np.array([math.cos(a), math.sin(a)]), np.array([math.sin(a), -math.cos(a)])
    p0 = np.array([15.0, 6.0]); p1 = p0 + 75 * d; p2 = p1 + 6 * u
    p3 = p2 - (p2[1] - 6.0) / d[1] * d
    outline = [(0, 0), (depth, 0), (depth, 6), tuple(p3), tuple(p2), tuple(p1), tuple(p0), (6, 6), (6, 14), (0, 14)]
    mesh = trimesh.creation.extrude_polygon(sg.polygon.orient(sg.Polygon(outline), 1.0), width)
    mesh.apply_transform(np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=float))
    mesh.apply_translation([0, 0, shift_z])
    return mesh


def house_scene(ridge=4.5, merge=False, dense=False, z_up=False, open_roof=False):
    import numpy as np
    import trimesh
    walls = trimesh.creation.box(extents=[6, 3, 4]); walls.apply_translation([0, 1.5, 0])
    corners = np.array([[x, y, z] for x in (-3.1, 3.1) for (y, z) in ((3.0, -2.1), (3.0, 2.1), (ridge, 0.0))])
    roof = trimesh.convex.convex_hull(corners)
    if open_roof:
        roof = trimesh.Trimesh(roof.vertices, roof.faces[1:], process=False)
    if dense:
        walls = walls.subdivide().subdivide().subdivide()
    if z_up:
        turn = trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])
        walls.apply_transform(turn); roof.apply_transform(turn)
    scene = trimesh.Scene()
    if merge:
        scene.add_geometry(trimesh.util.concatenate([walls, roof]), node_name="house", geom_name="house")
    else:
        scene.add_geometry(walls, node_name="walls", geom_name="walls")
        scene.add_geometry(roof, node_name="roof", geom_name="roof")
    return scene


THREE_OK = """<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;height:100%;overflow:hidden}canvas{display:block}</style></head>
<body><script type="module">
import * as THREE from './vendor/three.module.min.js';
const renderer = new THREE.WebGLRenderer({antialias: true}); renderer.setSize(innerWidth, innerHeight); document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x202028);
const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 100); camera.position.set(0, 3, 7); camera.lookAt(0, 0.5, 0);
scene.add(new THREE.AmbientLight(0xffffff, 0.5)); const sun = new THREE.DirectionalLight(0xffffff, 1.5); sun.position.set(3, 6, 4); scene.add(sun);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.MeshStandardMaterial({color: 0xcccccc})); ground.rotation.x = -Math.PI / 2; scene.add(ground);
const cube = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.2, 1.2), new THREE.MeshStandardMaterial({color: 0xff0000})); cube.position.set(-1.2, 0.6, 0); scene.add(cube);
const ball = new THREE.Mesh(new THREE.SphereGeometry(0.7, 32, 16), new THREE.MeshStandardMaterial({color: 0x0000ff})); ball.position.set(1.2, 0.7, 0); scene.add(ball);
renderer.render(scene, camera); window.__rendered = true;
</script></body></html>"""
THREE_BLANK = "<!doctype html><html><body><canvas style='width:100vw;height:100vh;display:block'></canvas><script>window.__rendered=true</script></body></html>"


def bracket_reference():
    import trimesh
    base = trimesh.creation.box(extents=[60, 40, 6]); base.apply_translation([0, 20, 3])
    wall = trimesh.creation.box(extents=[60, 6, 40]); wall.apply_translation([0, 37, 20])
    part = trimesh.boolean.union([base, wall], engine="manifold")
    cutters = []
    for x in (-18, 18):
        c = trimesh.creation.cylinder(radius=3, height=20, sections=32); c.apply_translation([x, 15, 3]); cutters.append(c)
    c = trimesh.creation.cylinder(radius=4, height=20, sections=32)
    c.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])); c.apply_translation([0, 37, 26]); cutters.append(c)
    part = trimesh.boolean.difference([part] + cutters, engine="manifold")
    vertices, faces = trimesh.remesh.subdivide_to_size(part.vertices, part.faces, max_edge=8.0)
    part = trimesh.Trimesh(vertices, faces, process=True)
    assert part.is_watertight and part.is_winding_consistent and part.volume > 0
    return part


def bracket_without_holes():
    """Known-wrong repair: watertight, one body, the right outline, but the three holes are gone."""
    import trimesh
    base = trimesh.creation.box(extents=[60, 40, 6]); base.apply_translation([0, 20, 3])
    wall = trimesh.creation.box(extents=[60, 6, 40]); wall.apply_translation([0, 37, 20])
    return trimesh.boolean.union([base, wall], engine="manifold")


def break_mesh(part, seed=20260927):
    """Holes, flipped faces and duplicates; no degenerate faces (one survived trimesh's own filter)."""
    import numpy as np
    import trimesh
    rng = np.random.default_rng(seed)
    faces, normals, vertices = part.faces.copy(), part.face_normals, part.vertices
    adjacency = part.vertex_faces
    remove = set()

    def flat_ring(vertex, normal):
        ring = [f for f in adjacency[vertex] if f >= 0]
        return ring if ring and all(np.dot(normals[f], normal) > 0.99999 for f in ring) else None

    for normal in ([0, 0, 1], [0, 1, 0]):
        for vertex in rng.permutation(len(vertices)):
            ring = flat_ring(vertex, normal)
            if ring and not (set(ring) & remove) and len(ring) >= 4:
                remove.update(ring); break
    bottom = [f for f in rng.permutation(len(faces)) if np.dot(normals[f], [0, 0, -1]) > 0.99999]
    picked = []
    for f in bottom:
        if all(len(set(faces[f]) & set(faces[g])) == 0 for g in list(remove) + picked):
            picked.append(f)
        if len(picked) == 2:
            break
    remove.update(picked)
    keep = np.array([i for i in range(len(faces)) if i not in remove])
    broken = faces[keep].copy()
    flip = rng.random(len(broken)) < 0.12
    broken[flip] = broken[flip][:, ::-1]
    duplicates = broken[rng.choice(len(broken), 6, replace=False)]
    all_faces = np.vstack([broken, duplicates])
    order = rng.permutation(len(all_faces))
    return trimesh.Trimesh(vertices, all_faces[order], process=False), {"removed_faces": len(remove), "flipped": int(flip.sum()),
                                                                       "duplicated": 6, "degenerate": 0}


def generic_repair(broken_path, out_path):
    """Feasibility control: a generic repair with the installed libraries."""
    import networkx as nx
    import numpy as np
    import trimesh
    mesh = trimesh.load(str(broken_path), force="mesh", process=True)
    mesh.update_faces(mesh.nondegenerate_faces()); mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices(); mesh.merge_vertices()
    edges = mesh.edges_sorted
    boundary = edges[trimesh.grouping.group_rows(edges, require_count=1)]
    graph = nx.Graph(); graph.add_edges_from(boundary.tolist())
    new_faces = []
    for component in nx.connected_components(graph):
        start = next(iter(component)); loop, previous, current = [start], None, start
        while True:
            following = [n for n in graph.neighbors(current) if n != previous]
            if not following or following[0] == start:
                break
            previous, current = current, following[0]; loop.append(current)
        for i in range(1, len(loop) - 1):
            new_faces.append([loop[0], loop[i], loop[i + 1]])
    mesh = trimesh.Trimesh(mesh.vertices, np.vstack([mesh.faces, np.array(new_faces, dtype=int)]) if new_faces else mesh.faces, process=True)
    trimesh.repair.fix_winding(mesh); trimesh.repair.fix_inversion(mesh)
    mesh.export(str(out_path))


def build_reference(reference: Path, three: Path) -> dict:
    reference.mkdir(parents=True, exist_ok=True)
    vendor = reference / "vendor"; vendor.mkdir(exist_ok=True)
    for name in ("three.module.min.js", "three.core.min.js"):
        shutil.copy(three / "build" / name, vendor / name)
    shutil.copy(three / "LICENSE", vendor / "LICENSE")
    part = bracket_reference(); part.export(str(reference / "bracket_reference.stl"))
    broken, damage = break_mesh(part); broken.export(str(reference / "broken.stl"))
    return damage


def main(argv=None):
    import trimesh
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path); parser.add_argument("controls", type=Path); parser.add_argument("report", type=Path)
    parser.add_argument("--three", type=Path, required=True, help="Folder of the three npm package (build/ and LICENSE).")
    parser.add_argument("--extra", type=Path, default=None)
    parser.add_argument("--node", required=True)
    parser.add_argument("--playwright-core", required=True)
    parser.add_argument("--chrome", required=True)
    args = parser.parse_args(argv)
    browser = ["--node", args.node, "--playwright-core", args.playwright_core, "--chrome", args.chrome]
    damage = build_reference(args.reference, args.three)
    part = trimesh.load(str(args.reference / "bracket_reference.stl"), force="mesh")
    rows = []

    def check(task, folder):
        """Grade one control; the checker runs again, up to three times, only when the checker itself failed."""
        for _ in range(3):
            done = subprocess.run([sys.executable, str(HERE / "checks.py"), task, str(folder), "--reference", str(args.reference)] + browser,
                                  capture_output=True, text=True, timeout=600)
            try:
                verdict = json.loads(done.stdout.strip().splitlines()[-1])
            except Exception:
                verdict = {"passed": None, "checks": [], "reason": "checker_crashed: " + done.stderr[-300:]}
            fault = verdict["passed"] is None or any(c["name"] in ("checker_ran", "render_harness") and not c["passed"]
                                                     for c in verdict["checks"])
            if not fault:
                break
        return verdict

    def control(task, name, build, expected_pass, expected_check=None, origin="added_2026_09_28", folder=None):
        if folder is None:
            folder = args.controls / name
            if folder.exists():
                shutil.rmtree(folder)
            folder.mkdir(parents=True)
            build(folder)
        verdict = check(task, folder)
        failing = [c["name"] for c in verdict["checks"] if not c["passed"]]
        ok = verdict["passed"] == expected_pass and (expected_check is None or expected_check in failing)
        rows.append({"task": task, "control": name, "origin": origin, "expected_pass": expected_pass,
                     "expected_failing_check": expected_check, "observed_pass": verdict["passed"], "failing_checks": failing,
                     "control_ok": ok, "reason": verdict["reason"]})

    import shapely.geometry as sg

    def page(html):
        def build(f):
            shutil.copytree(args.reference / "vendor", f / "vendor"); (f / "index.html").write_text(html)
        return build

    first = "first_2026_09_27"
    control("t1_gear", "t1_positive", lambda f: gear_mesh().export(str(f / "gear.stl")), True, origin=first)
    control("t1_gear", "t1_wrong_cylinder", lambda f: trimesh.creation.extrude_polygon(sg.Point(0, 0).buffer(26, 64).difference(sg.Point(0, 0).buffer(4, 32)), 8).export(str(f / "gear.stl")), False, "tooth_depth", first)
    control("t1_gear", "t1_wrong_23_teeth", lambda f: gear_mesh(teeth=23, module=52 / 25).export(str(f / "gear.stl")), False, "tooth_count", first)
    control("t1_gear", "t1_wrong_open", lambda f: trimesh.Trimesh(gear_mesh().vertices, gear_mesh().faces[5:], process=False).export(str(f / "gear.stl")), False, "watertight", first)
    control("t1_gear", "t1_wrong_no_bore", lambda f: trimesh.creation.extrude_polygon(sg.Polygon(gear_mesh().section(plane_origin=[0, 0, 4], plane_normal=[0, 0, 1]).to_2D()[0].polygons_full[0].exterior), 8).export(str(f / "gear.stl")), False, "bore", first)
    control("t1_gear", "t1_wrong_needle_teeth", lambda f: gear_mesh(flank=(0.48, 0.495, 0.505, 0.52)).export(str(f / "gear.stl")), False, "tooth_thickness")
    control("t1_gear", "t1_wrong_fat_teeth", lambda f: gear_mesh(flank=(0.02, 0.05, 0.95, 0.98)).export(str(f / "gear.stl")), False, "tooth_thickness")
    control("t2_stand", "t2_positive", lambda f: stand_mesh().export(str(f / "stand.stl")), True, origin=first)
    control("t2_stand", "t2_wrong_angle_55", lambda f: stand_mesh(angle=55).export(str(f / "stand.stl")), False, "support_face", first)
    control("t2_stand", "t2_wrong_footprint", lambda f: stand_mesh(width=90).export(str(f / "stand.stl")), False, "footprint_x", first)
    control("t2_stand", "t2_wrong_floating", lambda f: stand_mesh(shift_z=5).export(str(f / "stand.stl")), False, "on_z0", first)
    control("t2_stand", "t2_wrong_faces_back", lambda f: stand_mesh().apply_transform(trimesh.transformations.reflection_matrix([0, 35, 0], [0, 1, 0])).export(str(f / "stand.stl")), False, "support_face")
    control("t2_stand", "t2_wrong_two_pieces", lambda f: trimesh.util.concatenate([stand_mesh(), trimesh.creation.box(extents=[5, 5, 5], transform=trimesh.transformations.translation_matrix([40, 20, 20]))]).export(str(f / "stand.stl")), False, "single_body")
    control("t3_house", "t3_positive", lambda f: house_scene().export(str(f / "house.glb")), True, origin=first)
    control("t3_house", "t3_wrong_merged", lambda f: house_scene(merge=True).export(str(f / "house.glb")), False, "named_walls_and_roof", first)
    control("t3_house", "t3_wrong_ridge", lambda f: house_scene(ridge=5.2).export(str(f / "house.glb")), False, "roof_heights", first)
    control("t3_house", "t3_wrong_dense", lambda f: house_scene(dense=True).export(str(f / "house.glb")), False, "triangle_budget", first)
    control("t3_house", "t3_wrong_z_up", lambda f: house_scene(z_up=True).export(str(f / "house.glb")), False, "walls_size")
    control("t3_house", "t3_wrong_open_roof", lambda f: house_scene(open_roof=True).export(str(f / "house.glb")), False, "roof_watertight")
    control("t4_threejs", "t4_positive", page(THREE_OK), True, origin=first)
    control("t4_threejs", "t4_wrong_blank", page(THREE_BLANK), False, "red_cube_visible", first)
    control("t4_threejs", "t4_wrong_cdn", page(THREE_OK.replace("./vendor/three.module.min.js", "https://unpkg.com/three@0.180.0/build/three.module.js")), False, "no_external_requests", first)
    control("t4_threejs", "t4_wrong_console_error", page(THREE_OK.replace("window.__rendered = true;", "window.__rendered = true; console.error('boom');")), False, "no_console_errors", first)
    control("t4_threejs", "t4_wrong_no_sphere", page(THREE_OK.replace("scene.add(ball);", "")), False, "blue_sphere_visible", first)
    control("t4_threejs", "t4_wrong_small_canvas", page(THREE_OK.replace("renderer.setSize(innerWidth, innerHeight);", "renderer.setSize(300, 150);")), False, "canvas_fills_window")
    control("t4_threejs", "t4_wrong_never_rendered", page(THREE_OK.replace("window.__rendered = true;", "")), False, "rendered_flag")
    control("t5_repair", "t5_positive_reference", lambda f: shutil.copy(args.reference / "bracket_reference.stl", f / "repaired.stl"), True, origin=first)
    control("t5_repair", "t5_feasibility_generic_repair", lambda f: generic_repair(args.reference / "broken.stl", f / "repaired.stl"), True, origin=first)
    control("t5_repair", "t5_wrong_unrepaired", lambda f: shutil.copy(args.reference / "broken.stl", f / "repaired.stl"), False, "watertight", first)
    control("t5_repair", "t5_wrong_convex_hull", lambda f: part.convex_hull.export(str(f / "repaired.stl")), False, "volume_matches", first)
    control("t5_repair", "t5_wrong_scaled", lambda f: part.copy().apply_scale(1.05).export(str(f / "repaired.stl")), False, "volume_matches", first)
    control("t5_repair", "t5_wrong_inverted", lambda f: trimesh.Trimesh(part.vertices, part.faces[:, ::-1], process=False).export(str(f / "repaired.stl")), False, "positive_volume")
    control("t5_repair", "t5_wrong_holes_filled", lambda f: bracket_without_holes().export(str(f / "repaired.stl")), False, "shape_matches")
    if args.extra:
        for extra in json.loads(args.extra.read_text()):
            control(extra["task"], extra["control"], None, extra["expected_pass"], extra.get("expected_failing_check"),
                    origin=extra.get("origin", "real_output"), folder=Path(extra["folder"]))
    report = {"record_type": "showcase_3d_controls/v1", "damage": damage, "controls": rows,
              "all_controls_ok": all(r["control_ok"] for r in rows)}
    args.report.write_text(json.dumps(report, indent=1))
    for r in rows:
        print(("OK  " if r["control_ok"] else "BAD ") + f"{r['control']:34s} pass={r['observed_pass']} failing={r['failing_checks'][:3]}")
    print("ALL CONTROLS OK" if report["all_controls_ok"] else "SOME CONTROLS WRONG")
    return 0 if report["all_controls_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
