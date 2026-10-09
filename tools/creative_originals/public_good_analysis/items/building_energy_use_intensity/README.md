# Building energy use intensity by property type

Compute each building's site energy use intensity (energy per unit of floor area) and, per property type, the median and quartiles and the buildings above a Q3 + 3 x IQR fence, from benchmarking tables of floor area and annual site energy.

## What it does

Each row is one building with its property type, gross floor area and annual site energy use. The energy use intensity is site energy / floor area in the units the input names (kBtu per square foot by default, the unit US benchmarking ordinances publish; kWh and square metres are the alternatives). Per property type the function gives the buildings, the median and the 25th and 75th percentiles by linear interpolation between closest ranks, the high fence Q3 + 3 x IQR and the buildings above it, which are worth checking for a data error before they are compared.

## Run it

As a library:

```python
from building_energy_use_intensity import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 building_energy_use_intensity.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `rows` (array of object, required): one building: its id, property type, gross floor area and annual site energy use
- `area_unit` (one of square_feet, square_metres): unit of floor_area (default square_feet)
- `energy_unit` (one of kbtu, kwh): unit of site_energy (default kbtu)

## Output

- `energy_unit` (string, required)
- `area_unit` (string, required)
- `buildings` (array of object, required): each building's EUI, in building id order
- `property_types` (array of object, required): one summary per property type, in name order

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `floor_area_not_positive`: a floor area is zero or negative
- `negative_energy`: a site energy use is negative
- `duplicate_building`: two rows share a building id

## Checks

`examples/known_good.json` and the 3 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `building_energy_use_intensity.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The October 6, 2026 inventory of the owner's Kaggle download holds building energy benchmarking tables from several cities in this shape (floor area and annual site energy per property). Their licences are not established, so no row of them is copied; the examples are synthetic.

Dataset shape: building energy benchmarking tables with floor area and site energy use.

Proposed goals 7; targets 7.3; indicators 7.3.1. Energy use per unit of floor area is the building-scale form of the energy intensity that target 7.3 tracks (indicator 7.3.1 measures it per unit of GDP). The association is a proposal for reviewers, not a grant.

## Limits

Site energy only: source energy, weather normalization and occupancy are not applied, so buildings in different climates compare roughly. Units are labels; the function does not convert kBtu to kWh or square feet to square metres. A fence over few buildings flags little, and a high value can be real or a data error.

This item is a candidate component. Generating it did not approve or qualify it.
