"""Pixel-art rock with ore deposits: bevelled stone chunks, nuggets or gems and cracks, tileable (standard library).

The rock is a Voronoi diagram on a small art grid (``art_pixels`` square): every cell is a stone chunk with its own
shade, cell borders are one-pixel crevices, and chunk pixels next to a crevice on their upper or left side take the
light colour while those next to one on their lower or right side take the shadow colour. Ore clusters sit at
Poisson-disc points spread evenly over the torus; each cluster is a few small nuggets drawn as tiny sprites with a
highlight pixel at the top left and a shadow pixel at the bottom right, and gem ores add a white glint. Metal ores
are metallic in the metallic map, gems are smooth dielectrics. Cracks are short random walks. The art is enlarged
with nearest-neighbour sampling; heights, normals and occlusion are computed per art pixel.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "pixel_ore_rock"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.98]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "chunks", "type": "int", "default": 5, "minimum": 2, "maximum": 10,
     "meaning": "Stone chunks across the tile."},
    {"name": "ore", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of the evenly spread cluster positions that hold ore."},
    {"name": "nuggets", "type": "int", "default": 3, "minimum": 1, "maximum": 5,
     "meaning": "Nuggets or gems in each ore cluster."},
    {"name": "cracks", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of chunks with a crack."},
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
    "default": {"description": "Grey stone with gold nuggets.", "values": {}},
    "iron_ore": {"description": "Brown-grey stone with many rusty iron flecks.",
                 "values": {"ore": 0.8, "nuggets": 4, "chunks": 6}},
    "diamond_gems": {"description": "Dark deep-cave stone with a few bright cyan gems.",
                     "values": {"ore": 0.35, "nuggets": 2, "cracks": 0.5}},
    "copper_patina": {"description": "Warm stone with copper nuggets spotted with green patina.",
                      "values": {"ore": 0.6, "nuggets": 3, "chunks": 4}},
}
#: Per preset: crevice, stone shadow, stone, stone light, ore shadow, ore, ore highlight, glint (sRGB), whether the
#: ore is metal, and the ore roughness.
PALETTES = {
    "default": (("#26252a", "#4b4a52", "#626169", "#7c7b84", "#a26a12", "#e8b830", "#fff1a0", "#ffffff"), 1, 0.3),
    "iron_ore": (("#2b2522", "#4f4640", "#655a52", "#7d7168", "#7a3f22", "#c07a4c", "#e8b08a", "#f4d7c2"), 1, 0.45),
    "diamond_gems": (("#141418", "#2d2d36", "#3c3c48", "#50505e", "#1d7f9a", "#5ee0f2", "#d6fbff", "#ffffff"), 0,
                     0.12),
    "copper_patina": (("#2e2420", "#5a4a3f", "#74604f", "#8e7966", "#8a4a20", "#d97f3c", "#5fc2a2", "#fbd7b4"), 1,
                      0.35),
}
#: Roughness of stone and crevices.
STONE_ROUGHNESS = (0.88, 0.95)
#: Nugget sprites (offsets) for small and larger art grids.
SMALL_NUGGET = ((0, 0), (1, 0), (0, 1), (1, 1))
LARGE_NUGGETS = (((0, 0), (1, 0), (0, 1), (1, 1)), ((0, 0), (1, 0), (2, 0), (1, 1)), ((1, 0), (0, 1), (1, 1), (2, 1),
                 (1, 2)), ((0, 0), (1, 0), (1, 1), (2, 1)))


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The rock maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    codes, metal_ore, ore_rough = PALETTES[preset]
    crevice, shadow, stone, light, ore_dark, ore_mid, ore_light, glint = (tk.hex_rgb(code) for code in codes)
    art = p["art_pixels"]
    count = art * art
    chunks = min(p["chunks"], art // 4)
    cells = tk.voronoi(art, art, chunks, chunks, tk.hash_u32(seed, 1), jitter=0.9)
    grain = tk.fbm(art, art, max(4, art // 4), 2, tk.hash_u32(seed, 2))
    rng = tk.Rng(seed, 0x0E)
    tone = [rng.integer(-1, 1) for _ in range(chunks * chunks)]
    border = [cells["edge"][index] * art / chunks < 0.55 for index in range(count)]
    colour, heights = [None] * count, [0.0] * count
    rough, metal = [STONE_ROUGHNESS[0]] * count, [0.0] * count
    for y in range(art):
        for x in range(art):
            index = y * art + x
            if border[index]:
                colour[index], heights[index], rough[index] = crevice, 0.28, STONE_ROUGHNESS[1]
                continue
            lit = border[y * art + (x - 1) % art] or border[((y - 1) % art) * art + x]
            shaded = border[y * art + (x + 1) % art] or border[((y + 1) % art) * art + x]
            level = tone[cells["cell"][index]] + (1 if grain[index] > 0.4 else -1 if grain[index] < -0.45 else 0)
            face = (shadow, stone, light)[max(0, min(2, level + 1))]
            colour[index] = light if lit and not shaded else shadow if shaded else face
            heights[index] = (0.6 if lit and not shaded else 0.5 if shaded else 0.62) + 0.03 * grain[index]
    for cell in range(chunks * chunks):
        if not rng.chance(p["cracks"]):
            continue
        members = [index for index in range(count) if cells["cell"][index] == cell and not border[index]]
        if len(members) < 6:
            continue
        index = members[rng.integer(0, len(members) - 1)]
        x, y = index % art, index // art
        for _ in range(rng.integer(2, 4)):
            target = (y % art) * art + x % art
            if border[target]:
                break
            colour[target], heights[target] = crevice, 0.35
            step = rng.integer(0, 3)
            x, y = x + (1, 1, 0, -1)[step], y + (0, 1, 1, 1)[step]
    sprites = LARGE_NUGGETS if art >= 32 else (SMALL_NUGGET,)
    for u, v in tk.poisson_points(min(0.5, 7.0 / art), tk.hash_u32(seed, 3)):
        if not rng.chance(p["ore"]):
            continue
        cx, cy = int(u * art), int(v * art)
        for _ in range(p["nuggets"]):
            sprite = sprites[rng.integer(0, len(sprites) - 1)]
            ox, oy = cx + rng.integer(-2, 2), cy + rng.integer(-2, 2)
            right = max(dx for dx, _dy in sprite)
            bottom = max(dy for _dx, dy in sprite)
            for dx, dy in sprite:
                index = ((oy + dy) % art) * art + (ox + dx) % art
                shade = ore_light if (dx, dy) == sprite[0] else ore_dark if dx == right or dy == bottom else ore_mid
                colour[index], heights[index] = shade, 0.72
                rough[index], metal[index] = ore_rough, float(metal_ore)
            if not metal_ore or art >= 48:
                index = (oy % art) * art + ox % art
                colour[index] = glint
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.4 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 1.0)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     metallic=tk.upscale_nearest(metal, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
