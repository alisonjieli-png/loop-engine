# Baltor brand marks

Kind: brand assets. On September 23, 2026 the owner sent a sheet of 100 logo
variations and said "These are much much much better logos". Two of them were
traced into vector files the same day.

| Mark | File | Use |
|---|---|---|
| Tile, variation 52: a white husky head in profile on a navy rounded tile | [`baltor-mark.svg`](../../src/loop_engine/core/service_runtime/web_assets/baltor-mark.svg) | The header and footer mark and the page icon of the website. The icons `favicon-32.png`, `favicon-192.png` and `apple-touch-icon.png` in the same folder are drawn from it. |
| Summit, variation 23: the husky head as the peak of a mountain | [`baltor-summit.svg`](baltor-summit.svg) | The standalone mark for large uses. The website does not serve it yet. |

The colours are navy `#0E1E3F` and white. The tile is a navy rounded square
with a white husky. The summit is navy only, and the face of the husky is left
open, so the summit belongs on a white or light ground.

The rule: the tile is the favicon and the header mark. The summit is for large
uses and does not replace the tile at small sizes.

The published tile leaves out four white fragments that the tracing took from
the paper around the tile's rounded corners. On a dark ground they showed as
white corners, and the two lower ones cut into the tile. The husky and the tile
are the traced shapes. The three icons were drawn again from the repaired
tile, and a browser check in `tools/check_service_workspace.mjs` fails when
the mark or an icon shows white outside the rounded tile.
