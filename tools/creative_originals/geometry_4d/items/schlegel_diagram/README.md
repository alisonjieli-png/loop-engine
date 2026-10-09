# Schlegel diagrams of convex 4-polytopes

`schlegel_diagram.py` draws a 4D polytope the way it looks through one of its cells: that cell becomes the outer
boundary and every other cell nests inside it without overlapping. It writes the diagram as a glTF wireframe (LINES
or tubes) with the outer cell as a translucent shell. It reads the six regular 4-polytopes or any
`fourd_polytope/v1` record.

## Mathematics

Take a cell F with outward unit normal n, hyperplane n . p = h and centroid c. Put the eye at e = c + t n, just
outside F. Every other cell g with hyperplane n_g . p = h_g must keep the eye on its inner side; t is half of the
largest value allowed by those inequalities, so F is the only cell the eye sees from outside. Each vertex v is
projected centrally from e onto F's hyperplane: p = e + s (v - e) with s = (h - n . e)/(n . (v - e)). F's own
vertices stay where they are, and every other vertex lands inside F. Points are written in F's hyperplane basis
around c. For the tesseract seen through a cube, the eye sits at twice the cube's distance and the opposite cube
appears centred at one third of the size. The regular polytopes are built as Coxeter group orbits, with cells
orthogonal to the images of one fundamental weight.

## Run it

```
python schlegel_diagram.py --polytope 24cell --style tubes --out schlegel_24cell.gltf
python schlegel_diagram.py --polytope 120cell --style lines --out schlegel_120cell.gltf
python schlegel_diagram.py --polytope tesseract --out tesseract_schlegel.gltf
python schlegel_diagram.py --polytope my_polytope.json --cell 3 --out mine.gltf
```

```python
import schlegel_diagram as sd
shape = sd.load_polytope("600cell")
points = sd.project(shape, cell=0)
sd.inside_outer_cell(shape, points)    # True
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--polytope` | 24cell | `5cell`, `tesseract`, `16cell`, `24cell`, `120cell`, `600cell`, or a polytope JSON path. |
| `--cell` | 0 | Index of the cell to look through. |
| `--style` | tubes | `tubes` or `lines` (LINES primitive, lighter for the 120-cell and 600-cell). |
| `--radius` | 1.2 percent of the size | Tube radius. |
| `--sides` | 6 | Sides of each tube. |
| `--shell` | on | Draw the outer cell as a translucent shell. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: the 24-cell seen through one octahedron. `schlegel` holds the tube wireframe (1440 vertices)
coloured from amber (outer) to blue (deepest); `outer_cell` is the octahedron as a translucent shell (24
vertices). The CLI example in the contract writes the 120-cell as LINES.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`; enable `vertex_color_use_as_albedo` on the wire material for the depth colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

The polytope must be convex and its record must list cells. The eye sits halfway to the nearest other cell
hyperplane; other choices change how deep the nesting looks, not its structure. LINES are one pixel wide in most
viewers, and the shell relies on the viewer's alpha sorting.
