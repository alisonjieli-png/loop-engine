"""Pixel-art stone brick wall: bevelled bricks, one-pixel mortar, cracks and moss, tileable maps (standard library).

The wall is laid out on a small art grid (``art_pixels`` square): courses split the height at whole art pixels, and
each course is cut into bricks at jittered positions with its own offset, so joints stagger and the layout wraps
around the tile. Mortar is the top row of each course and the left column of each brick, which keeps exactly one
mortar line between neighbours across the tile edges. Inside a brick the first row and column take the highlight
colour and the last row and column the shadow colour, the classic bevel of a light from the top left. Stone grain
is posterized noise; cracks are short random walks; moss grows from the joints where a noise field allows it. The
art is enlarged with nearest-neighbour sampling, and heights, normals and occlusion are computed per art pixel.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "pixel_stone_bricks"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "courses", "type": "int", "default": 4, "minimum": 2, "maximum": 8,
     "meaning": "Brick courses across the tile height."},
    {"name": "bricks_per_course", "type": "int", "default": 2, "minimum": 1, "maximum": 6,
     "meaning": "Bricks in each course across the tile width."},
    {"name": "irregularity", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Random variation of brick lengths and course offsets (0 is a regular running bond)."},
    {"name": "cracks", "type": "float", "default": 0.25, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of bricks with a crack."},
    {"name": "moss", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Moss growing from the joints."},
    {"name": "relief", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 2.0,
     "meaning": "Strength of the per-pixel normal map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey castle stone in staggered courses with a little moss.", "values": {}},
    "sandstone": {"description": "Warm sandstone blocks, three courses, crisp and clean.",
                  "values": {"courses": 3, "bricks_per_course": 2, "irregularity": 0.6, "cracks": 0.1,
                             "moss": 0.0}},
    "mossy_ruin": {"description": "Old green-grey ruin stones, cracked and overgrown.",
                   "values": {"cracks": 0.7, "moss": 0.75, "irregularity": 0.8}},
    "red_brick": {"description": "Small red bricks in a regular running bond with pale mortar.",
                  "values": {"courses": 8, "bricks_per_course": 4, "irregularity": 0.0, "cracks": 0.1,
                             "moss": 0.0}},
}
#: Per preset: mortar, mortar shadow, stone shadow, stone base, stone light, bevel highlight, moss dark and light
#: (sRGB).
PALETTES = {
    "default": ("#3b3a40", "#2a292e", "#55555f", "#6f707a", "#878894", "#a9aab4", "#3f5a2c", "#5d7f38"),
    "sandstone": ("#6b5236", "#4f3c28", "#a07a4c", "#bd925c", "#d2aa70", "#e9c98f", "#5c6a2e", "#7d8c3c"),
    "mossy_ruin": ("#2f3a33", "#202822", "#4c5a52", "#62706a", "#78877f", "#9aa79e", "#3a5d24", "#62892f"),
    "red_brick": ("#b9b0a2", "#8d8578", "#7d2f22", "#9b3c2a", "#b24c34", "#cf6a4b", "#4b6a2b", "#6b8a35"),
}
#: Roughness of mortar, brick face, top-left bevel and bottom-right bevel (indexed by the pixel role), and of moss.
ROLE_ROUGHNESS = (0.95, 0.84, 0.78, 0.8)
MOSS_ROUGHNESS = 0.92


def _cuts(rng, length: int, pieces: int, jitter: float) -> list:
    """Cut positions 0 <= c < length of ``pieces`` pieces, evenly spaced and jittered, at least 3 art pixels apart."""
    step = length / pieces
    cuts = []
    for k in range(pieces):
        cut = round(k * step + (rng.random() - 0.5) * jitter * step * 0.6)
        cuts.append(cut)
    cuts = sorted(set(cut % length for cut in cuts))
    kept = [cuts[0]]
    for cut in cuts[1:]:
        if cut - kept[-1] >= 3 and length + kept[0] - cut >= 3:
            kept.append(cut)
    return kept


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The brick maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    mortar, mortar_dark, shadow, base, light, highlight, moss_dark, moss_light = (
        tk.hex_rgb(code) for code in PALETTES[preset])
    art = p["art_pixels"]
    count = art * art
    rng = tk.Rng(seed, 0x51)
    courses = min(p["courses"], art // 4)
    rows = [round(k * art / courses) for k in range(courses + 1)]
    brick_of = [0] * count
    role = [0] * count  # 0 mortar, 1 face, 2 top or left bevel, 3 bottom or right bevel
    bricks = 0
    for course in range(courses):
        top, bottom = rows[course], rows[course + 1]
        pieces = max(1, min(p["bricks_per_course"], art // 4))
        offset = round((course % 2) * art / pieces * 0.5 + (rng.random() - 0.5) * p["irregularity"] * art / pieces)
        cuts = [(cut + offset) % art for cut in _cuts(rng, art, pieces, p["irregularity"])]
        cuts.sort()
        starts = {cut: bricks + n for n, cut in enumerate(cuts)}
        bricks += len(cuts)
        for x in range(art):
            behind = [cut for cut in cuts if cut <= x]
            start = behind[-1] if behind else cuts[-1] - art
            ends = [cut for cut in cuts if cut > x]
            end = ends[0] if ends else cuts[0] + art
            for y in range(top, bottom):
                index = y * art + x
                brick_of[index] = starts[start % art]
                if y == top or x == start % art:
                    role[index] = 0
                elif y == top + 1 or x == start + 1 or x == start % art + 1:
                    role[index] = 2
                elif y == bottom - 1 or x == end - 1 or x == end % art - 1:
                    role[index] = 3
                else:
                    role[index] = 1
    grain = tk.fbm(art, art, max(4, art // 4), 2, tk.hash_u32(seed, 2))
    growth = tk.fbm(art, art, max(2, art // 8), 3, tk.hash_u32(seed, 3))
    tint = [rng.uniform(-1.0, 1.0) for _ in range(bricks)]
    colour, heights, rough = [None] * count, [0.0] * count, [0.0] * count
    for index in range(count):
        kind = role[index]
        if kind == 0:
            colour[index], heights[index], rough[index] = mortar, 0.12, ROLE_ROUGHNESS[0]
            continue
        shade = tint[brick_of[index]] * 0.6 + grain[index] * 1.4 + (tk.bayer4(index % art, index // art) - 0.5) * 0.5
        face = shadow if shade < -0.75 else light if shade > 0.75 else base
        colour[index] = highlight if kind == 2 else shadow if kind == 3 else face
        heights[index] = (0.52 if kind == 2 else 0.5 if kind == 3 else 0.66) + 0.04 * grain[index]
        rough[index] = ROLE_ROUGHNESS[kind]
    for brick in range(bricks):
        if not rng.chance(p["cracks"]):
            continue
        members = [index for index in range(count) if brick_of[index] == brick and role[index] == 1]
        if not members:
            continue
        index = members[rng.integer(0, len(members) - 1)]
        x, y = index % art, index // art
        for _ in range(rng.integer(3, 6)):
            target = (y % art) * art + x % art
            if role[target] == 0 or brick_of[target] != brick:
                break
            colour[target], heights[target], rough[target] = mortar_dark, 0.3, ROLE_ROUGHNESS[0]
            step = rng.integer(0, 3)
            x += (-1, 1, 0, 1)[step]
            y += (1, 1, 1, 0)[step]
    for y in range(art):
        for x in range(art):
            index = y * art + x
            below = ((y + 1) % art) * art + x
            near_joint = role[index] == 0 or role[below] == 0 or role[index] == 3
            level = growth[index] + 0.9 * p["moss"] - 0.75 + (0.25 if near_joint else -0.2) \
                + 0.2 * (tk.bayer4(x, y) - 0.5)
            if p["moss"] > 0.0 and level > 0.0:
                colour[index] = moss_light if level > 0.2 and role[index] != 0 else moss_dark
                heights[index] = max(heights[index], 0.55 if role[index] != 0 else 0.3)
                rough[index] = MOSS_ROUGHNESS
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.5 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 1.0)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
