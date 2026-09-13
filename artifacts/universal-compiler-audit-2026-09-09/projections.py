"""Export existing canonical audit/diagram projections, not a new authority."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/home/username/loop-engine')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from loop_engine.core.component_inventory import ComponentInventoryRequest, run_component_inventory
from loop_engine.code_nodes.architecture_diagram import DIAGRAMS, render_document

if __name__ == '__main__':
    inventory = run_component_inventory(ComponentInventoryRequest(str(ROOT / 'src/loop_engine')))
    with (HERE / 'canonical-component-inventory.json').open('x') as stream:
        json.dump(inventory, stream, indent=2, default=str)
        stream.write('\n')
    with (HERE / 'CURRENT-GENERATED-VIEWS.md').open('x') as stream:
        stream.write(render_document())
    views = {
        'record_type': 'generated_view_audit/v1',
        'models': [x.to_dict() for x in DIAGRAMS],
        'source_sha256': hashlib.sha256((ROOT / 'src/loop_engine/code_nodes/architecture_diagram.py').read_bytes()).hexdigest(),
        'view_count': len(DIAGRAMS),
        'verification': 'Existing typed model and generator. No browser/PlantUML visual rendering performed.',
        'missing_mandate_fields': ['structured protocol per edge', 'structured synchronous/asynchronous behavior per edge', 'structured trust/authority per edge'],
        'all_requested_c4_views_implemented': False,
    }
    with (HERE / 'generated-view-audit.json').open('x') as stream:
        json.dump(views, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'files': len(inventory['files']), 'symbols': len(inventory['symbols']),
                      'explicit_components': len(inventory['explicit_components']), 'views': len(DIAGRAMS)}))
