# Layer exception lists with a declared precedence

Keep exceptions for text cleaning in layers, from general to specific. Merge the layers in a fixed order, so every decision can be traced to the entry that made it.

## When to use it

Use it when cleaning rules need exceptions: surnames with internal capitals, tokens that stay in upper case, legal suffixes, null markers. Use it when one dataset needs entries that would be wrong for every other dataset.

## Steps

1. Declare the layers, lowest precedence first:
   - the packaged file with general business and personal name conventions;
   - an exception file supplied in the task folder;
   - casings that the column itself proves;
   - parameters written on one rule;
   - recorded answers from a model, from research or from a person.
2. Give each layer an identifier, a source, a version and a digest of its content.
3. Validate each layer. Refuse an unknown kind of list. Refuse a list kind that is not a list and a mapping kind that is not a mapping.
4. Load a task folder file only from inside the task folder. Refuse a path that leaves it.
5. Merge in order. A later layer overrides a mapping entry. A later layer extends a list without repeating entries.
6. Learn column evidence only from values that carry case information. A token needs at least two votes, and its dominant written form needs at least 80 percent of them.
7. Make every correction name the entry or the signal that decided it.

## Checks

- In a column where `iPhone Repair` appears twice in mixed case, `IPHONE REPAIR` becomes `iPhone Repair` with the reason `column_evidence:iPhone`. Without the evidence layer the result is `Iphone Repair`.
- The merged result does not depend on anything except the layers and their order.
- A path such as `../other/exceptions.yaml` is refused.

## Known-wrong example

One customer spells a brand `ACME-tech`, and someone adds that entry to the packaged general file. Every other dataset now inherits one customer's spelling. The entry belongs in that customer's task folder file, which has higher precedence and affects only that task.

## What to record

- The layers that were used, in order, each with its version and digest.
- The entry or signal named by each correction.
- Each recorded answer that was added as a new top layer entry.

## Source

- `src/loop_engine/code_nodes/text_conformance.py`: `ExceptionCatalogLayer`, `merge_layers`, `catalog_layer_from_file` and `evidence_layer`.
- `src/loop_engine/code_nodes/text_conformance_operations.py`: `learn_column_evidence`.
- `src/loop_engine/data/text_conformance_catalogs.yaml`: the packaged layer.

Licence: MIT. Compiled from revision 1700841. Reading the packaged file and a YAML task file needs the PyYAML package.
