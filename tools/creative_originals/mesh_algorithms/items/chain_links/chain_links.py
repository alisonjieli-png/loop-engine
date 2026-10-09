"""Chain: interlocking oval links (stadium tori), one link mesh instanced by glTF nodes at alternating angles.

Command line: python3 chain_links.py --output chain.gltf --links 7 --straight 0.4 --end-radius 0.3 --wire-radius 0.08
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "links", "type": "int", "default": 7, "unit": "count", "minimum": 1, "maximum": 10000,
     "meaning": "Number of links."},
    {"name": "straight", "type": "float", "default": 0.4, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Length of the straight sides of each link's centre line."},
    {"name": "end_radius", "type": "float", "default": 0.3, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius of the round ends of the centre line; above 2 * wire_radius + clearance."},
    {"name": "wire_radius", "type": "float", "default": 0.08, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius of the wire."},
    {"name": "clearance", "type": "float", "default": 0.02, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Gap left between neighbouring links where they hook."},
    {"name": "samples", "type": "int", "default": 64, "unit": "count", "minimum": 8, "maximum": 100000,
     "meaning": "Samples along each link's centre line."},
    {"name": "sides", "type": "int", "default": 12, "unit": "count", "minimum": 3, "maximum": 1024,
     "meaning": "Divisions around the wire."},
]


def stadium_point(fraction, straight=0.4, end_radius=0.3):
    """(position, unit tangent) on the stadium centre line in the XZ plane at arc-length ``fraction`` in [0, 1),
    starting at the middle of the +Z straight side and running counter-clockwise seen from +Y."""
    perimeter = 2.0 * straight + 2.0 * math.pi * end_radius
    s = (fraction % 1.0) * perimeter
    half = straight / 2.0
    arc = math.pi * end_radius
    if s < half:
        return (s, 0.0, end_radius), (1.0, 0.0, 0.0)
    s -= half
    if s < arc:
        angle = s / end_radius
        return ((half + end_radius * math.sin(angle), 0.0, end_radius * math.cos(angle)),
                (math.cos(angle), 0.0, -math.sin(angle)))
    s -= arc
    if s < straight:
        return (half - s, 0.0, -end_radius), (-1.0, 0.0, 0.0)
    s -= straight
    if s < arc:
        angle = s / end_radius
        return ((-half - end_radius * math.sin(angle), 0.0, -end_radius * math.cos(angle)),
                (-math.cos(angle), 0.0, math.sin(angle)))
    s -= arc
    return (-half + s, 0.0, end_radius), (1.0, 0.0, 0.0)


def link_mesh(straight=0.4, end_radius=0.3, wire_radius=0.08, samples=64, sides=12):
    """One closed link in the XZ plane centred at the origin: samples * sides vertices and quads (torus
    topology). The centre line is planar, so the frame is the in-plane normal and +Y."""
    if min(end_radius, wire_radius) <= 0 or straight < 0 or samples < 8 or sides < 3:
        raise meshkit.MeshError("parameter_invalid", "radii > 0, straight >= 0, samples >= 8, sides >= 3")
    vertices, normals, faces = [], [], []
    for i in range(samples):
        center, tangent = stadium_point(i / samples, straight, end_radius)
        outward = (-tangent[2], 0.0, tangent[0])
        for j in range(sides):
            angle = 2.0 * math.pi * j / sides
            direction = meshkit.vadd(meshkit.vscale(outward, math.cos(angle)), (0.0, math.sin(angle), 0.0))
            vertices.append(meshkit.vadd(center, meshkit.vscale(direction, wire_radius)))
            normals.append(direction)
    for i in range(samples):
        ni = (i + 1) % samples
        for j in range(sides):
            nj = (j + 1) % sides
            faces.append((i * sides + j, ni * sides + j, ni * sides + nj, i * sides + nj))
    return meshkit.Mesh(vertices, faces, normals=normals, name="chain_link",
                        material=meshkit.material("steel", (0.62, 0.64, 0.68, 1.0), metallic=0.85, roughness=0.3))


def chain(links=7, straight=0.4, end_radius=0.3, wire_radius=0.08, clearance=0.02, samples=64, sides=12):
    """A scene dict {"meshes": [link], "nodes": [...]}: a root node and one child node per link along X.

    Link k sits at x = (k - (links - 1) / 2) * pitch with pitch = straight + 2 end_radius - 2 wire_radius -
    clearance, and every odd link is turned 90 degrees about X, so neighbours hook through each other."""
    if end_radius <= 2.0 * wire_radius + clearance:
        raise meshkit.MeshError("parameter_invalid", "end_radius must exceed 2 * wire_radius + clearance")
    pitch = straight + 2.0 * end_radius - 2.0 * wire_radius - clearance
    quarter = meshkit.quaternion_from_axis_angle((1.0, 0.0, 0.0), 0.5 * math.pi)
    nodes = [{"name": "chain", "children": list(range(1, links + 1))}]
    for k in range(links):
        node = {"name": f"link_{k}", "mesh": 0, "translation": ((k - (links - 1) / 2.0) * pitch, 0.0, 0.0)}
        if k % 2:
            node["rotation"] = quarter
        nodes.append(node)
    return {"meshes": [link_mesh(straight, end_radius, wire_radius, samples, sides)], "nodes": nodes}


def chain_mesh(links=7, straight=0.4, end_radius=0.3, wire_radius=0.08, clearance=0.02, samples=64, sides=12):
    """The chain baked into one mesh (each link transformed by its node), for measuring and for OBJ."""
    scene = chain(links, straight, end_radius, wire_radius, clearance, samples, sides)
    parts = []
    for node in scene["nodes"][1:]:
        matrix = meshkit.trs_matrix(node["translation"], node.get("rotation", (0.0, 0.0, 0.0, 1.0)))
        parts.append(meshkit.transformed(scene["meshes"][0], matrix))
    return meshkit.combine(parts, "chain")


def main(argv=None):
    """Command line: write the chain (instanced nodes in .gltf, baked in .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=chain)


if __name__ == "__main__":
    raise SystemExit(main())
