"""Export the open .blend to glTF (separate .gltf and .bin) with the exporter's default settings.

    blender --background SCENE.blend --python export_gltf.py -- OUTPUT.gltf [name=value ...]

Extra name=value pairs are passed to the exporter (true, false, integers and plain words are converted).
"""
import json
import sys

import bpy


def value(text):
    lowered = text.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:]
    options = dict(pair.split("=", 1) for pair in arguments[1:])
    options = {key: value(item) for key, item in options.items()}
    result = bpy.ops.export_scene.gltf(filepath=arguments[0], export_format="GLTF_SEPARATE", **options)
    print("EXPORTED", json.dumps(sorted(result)), json.dumps(options, sort_keys=True))


main()
