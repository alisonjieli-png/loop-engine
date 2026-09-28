"""Author contracts and explicit acceptance cases before writing the candidate tool."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PACKAGE = BASE / 'audit_wikilink_resolution'
ID = PACKAGE.name
PROFILE = 'bounded_markdown_wikilinks/v1'


def write(path, value):
    target = PACKAGE / path
    if target.exists():
        raise ValueError('preserve_existing_payload')
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required,
            'additionalProperties': False}


path = {'type': 'string', 'minLength': 4, 'maxLength': 256,
        'pattern': r'^[^/\\:#|\[\]\x00-\x1f\x7f]+(?:/[^/\\:#|\[\]\x00-\x1f\x7f]+)*\.md$',
        'not': {'pattern': r'[\x00-\x1f\x7f]'}}
sha = {'type': 'string', 'minLength': 64, 'maxLength': 64, 'pattern': '^[0-9a-f]{64}$'}
input_schema = obj({'record_type': {'const': ID + '_request/v1'}, 'syntax_profile': {'const': PROFILE},
                    'source_path': path, 'text': {'type': 'string', 'maxLength': 32768},
                    'note_paths': {'type': 'array', 'minItems': 1, 'maxItems': 256, 'uniqueItems': True, 'items': path},
                    'expected_sha256': sha}, ['record_type', 'syntax_profile', 'source_path', 'text', 'note_paths'])
input_schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
input_schema['description'] = 'Additional path-segment, source-membership, wire-byte and syntax limits are specified in references/profile.md.'
number = {'type': 'integer', 'minimum': 0, 'maximum': 32768}
nullable = {'type': ['string', 'null'], 'maxLength': 32768}
link = obj({'start': number, 'end': number, 'line': {'type': 'integer', 'minimum': 1, 'maximum': 32769},
            'column': {'type': 'integer', 'minimum': 1, 'maximum': 32769},
            'raw': {'type': 'string', 'maxLength': 32768}, 'target': nullable, 'fragment': nullable,
            'display': nullable, 'embedded': {'type': 'boolean'},
            'status': {'enum': ['resolved', 'missing', 'ambiguous', 'unsupported']},
            'candidate_paths': {'type': 'array', 'maxItems': 256, 'uniqueItems': True, 'items': path},
            'reason': {'enum': ['unique_note', 'note_not_found', 'multiple_note_targets', 'invalid_link_syntax', 'unclosed_or_nested_link']},
            'fragment_status': {'enum': ['absent', 'not_checked']}})
success = obj({'record_type': {'const': ID + '_result/v1'}, 'syntax_profile': {'const': PROFILE},
               'source_path': path, 'source_sha256': sha, 'complete_markdown_audit': {'const': False},
               'links': {'type': 'array', 'maxItems': 256, 'items': link},
               'counts': obj({x: {'type': 'integer', 'minimum': 0, 'maximum': 256} for x in ('resolved', 'missing', 'ambiguous', 'unsupported')})})
error = obj({'error': {'enum': ['invalid_input', 'source_digest_mismatch', 'unclosed_frontmatter', 'link_limit_exceeded', 'output_limit_exceeded']}})
output_schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'oneOf': [success, error]}
write('contracts/input.schema.json', input_schema)
write('contracts/output.schema.json', output_schema)


def request(text, notes=('source.md', 'Roadmap.md'), source='source.md', **extra):
    return {'record_type': ID + '_request/v1', 'syntax_profile': PROFILE, 'source_path': source,
            'text': text, 'note_paths': list(notes), **extra}


def expected(req, specs):
    text = req['text']
    links = []
    for spec in specs:
        token, candidates = spec[0], spec[1]
        options = spec[2] if len(spec) == 3 else {}
        start = options.get('start', text.index(token))
        raw = options.get('raw', token[2:-2])
        target = options.get('target', raw.split('|', 1)[0].split('#', 1)[0])
        fragment = options.get('fragment')
        status = options.get('status', 'resolved' if len(candidates) == 1 else 'ambiguous' if candidates else 'missing')
        reason = options.get('reason', {'resolved': 'unique_note', 'ambiguous': 'multiple_note_targets', 'missing': 'note_not_found', 'unsupported': 'invalid_link_syntax'}[status])
        links.append({'start': start, 'end': start + len(token), 'line': text.count('\n', 0, start) + 1,
                      'column': start - text.rfind('\n', 0, start), 'raw': raw, 'target': target,
                      'fragment': fragment, 'display': options.get('display'), 'embedded': options.get('embedded', False),
                      'status': status, 'candidate_paths': sorted(candidates), 'reason': reason,
                      'fragment_status': 'not_checked' if fragment is not None else 'absent'})
    return {'record_type': ID + '_result/v1', 'syntax_profile': PROFILE, 'source_path': req['source_path'],
            'source_sha256': hashlib.sha256(text.encode()).hexdigest(), 'complete_markdown_audit': False,
            'links': links, 'counts': {s: sum(x['status'] == s for x in links) for s in ('resolved', 'missing', 'ambiguous', 'unsupported')}}


cases = []


def case(name, req, specs=(), error=None):
    cases.append({'name': name, 'input': req, 'expected_exit': 2 if error else 0,
                  'expected': {'error': error} if error else expected(req, specs)})


example = request('[[Roadmap]] [[Missing]] [[Plan|work]] [[Roadmap#Next]]',
                  ('source.md', 'Roadmap.md', 'a/Plan.md', 'b/Plan.md'))
specs = [('[[Roadmap]]', ['Roadmap.md']), ('[[Missing]]', []),
         ('[[Plan|work]]', ['a/Plan.md', 'b/Plan.md'], {'display': 'work'}),
         ('[[Roadmap#Next]]', ['Roadmap.md'], {'fragment': 'Next'})]
write('examples/input.json', example)
write('examples/output.json', expected(example, specs))
case('four_distinct_resolution_outcomes', example, specs)
case('root_path_does_not_use_current_directory', request('[[Roadmap]] [[root/Roadmap.md]]',
     ('root/source.md', 'root/Roadmap.md', 'elsewhere/Roadmap.md'), 'root/source.md'),
     [('[[Roadmap]]', ['root/Roadmap.md', 'elsewhere/Roadmap.md']), ('[[root/Roadmap.md]]', ['root/Roadmap.md'])])
case('same_note_fragment_is_not_verified', request('[[#Missing heading]]'), [('[[#Missing heading]]', ['source.md'], {'fragment': 'Missing heading'})])
case('block_fragment_and_note_embed', request('![[Roadmap#^block|label]]'), [('[[Roadmap#^block|label]]', ['Roadmap.md'], {'embedded': True, 'fragment': '^block', 'display': 'label'})])
case('case_sensitive_identity', request('[[roadmap]]'), [('[[roadmap]]', [])])
case('unicode_normalization_not_inferred', request('[[e\u0301]]', ('source.md', 'é.md')), [('[[e\u0301]]', [])])
case('unicode_codepoint_offsets', request('🐕\nxx [[Roadmap]]'), [('[[Roadmap]]', ['Roadmap.md'])])
case('fenced_example_is_not_active', request('```md\n[[Ghost]]\n```\n[[Roadmap]]'), [('[[Roadmap]]', ['Roadmap.md'])])
case('longer_fence_requires_matching_character_and_length', request('````md\n[[Ghost]]\n```\n[[Ghost2]]\n````\n[[Roadmap]]'), [('[[Roadmap]]', ['Roadmap.md'])])
case('tilde_fence_unclosed_masks_to_end', request('~~~\n[[Ghost]]'), [])
case('same_line_backtick_runs', request('``[[Ghost]] ` x`` [[Roadmap]]'), [('[[Roadmap]]', ['Roadmap.md'])])
case('unmatched_inline_backtick_is_literal', request('` [[Roadmap]]'), [('[[Roadmap]]', ['Roadmap.md'])])
case('comments_are_not_links', request('%% [[Ghost]] %% <!-- [[Ghost2]] --> [[Roadmap]]'), [('[[Roadmap]]', ['Roadmap.md'])])
case('unclosed_comment_masks_to_end', request('%% [[Ghost]]'), [])
case('frontmatter_and_indented_line', request('---\nalias: [[Ghost]]\n---\n    [[Ghost2]]\n[[Roadmap]]'), [('[[Roadmap]]', ['Roadmap.md'])])
case('unclosed_frontmatter_refuses', request('---\nalias: [[Ghost]]'), error='unclosed_frontmatter')
case('odd_escape_ignored_even_escape_active', request('\\[[Ghost]] \\\\[[Roadmap]]'), [('[[Roadmap]]', ['Roadmap.md'])])
case('escaped_embed_marker_not_embed', request('\\![[Roadmap]]'), [('[[Roadmap]]', ['Roadmap.md'])])
case('aliases_are_display_only', request('[[Roadmap|Missing]]'), [('[[Roadmap|Missing]]', ['Roadmap.md'], {'display': 'Missing'})])
case('multiple_labels_unsupported', request('[[Roadmap|a|b]]'), [('[[Roadmap|a|b]]', [], {'target': None, 'status': 'unsupported'})])
case('parent_target_unsupported', request('[[../Roadmap]]'), [('[[../Roadmap]]', [], {'target': None, 'status': 'unsupported'})])
case('empty_link_unsupported', request('[[]]'), [('[[]]', [], {'target': None, 'status': 'unsupported'})])
case('unclosed_link_reported', request('[[Roadmap'), [('[[Roadmap', [], {'raw': 'Roadmap', 'target': None, 'status': 'unsupported', 'reason': 'unclosed_or_nested_link'})])
case('empty_text', request(''), [])
case('digest_matches', request('[[Roadmap]]', expected_sha256=hashlib.sha256(b'[[Roadmap]]').hexdigest()), [('[[Roadmap]]', ['Roadmap.md'])])
case('digest_mismatch', request('[[Roadmap]]', expected_sha256='0'*64), error='source_digest_mismatch')
case('source_must_exist', request('', ('Roadmap.md',)), error='invalid_input')
case('duplicate_paths_refused', request('', ('source.md', 'source.md')), error='invalid_input')
case('unsafe_inventory_path_refused', request('', ('source.md', '../bad.md')), error='invalid_input')
case('path_segment_whitespace_refused', request('', ('source.md', 'folder /bad.md')), error='invalid_input')
case('unknown_field_refused', request('', unexpected=True), error='invalid_input')
case('retired_profile_refused', {**request(''), 'syntax_profile': 'bounded_markdown_wikilinks/v0'}, error='invalid_input')
case('link_count_bounded', request('[[Roadmap]] '*257), error='link_limit_exceeded')
cases.extend([
 {'name': 'duplicate_json_key_refused', 'raw_input': '{"record_type":1,"record_type":2}', 'expected_exit': 2, 'expected': {'error': 'invalid_input'}},
 {'name': 'nonfinite_refused', 'raw_input': '{"x":NaN}', 'expected_exit': 2, 'expected': {'error': 'invalid_input'}},
 {'name': 'invalid_utf8_refused', 'input_hex': 'ff', 'expected_exit': 2, 'expected': {'error': 'invalid_input'}},
 {'name': 'wire_bytes_bounded', 'raw_input': ' '*65537, 'expected_exit': 2, 'expected': {'error': 'invalid_input'}},
])
write('verification/cases.json', cases)
(BASE/'authors/contracts-first.json').write_text(json.dumps({'operation': ID, 'stage': 'contracts_and_cases_before_executable',
     'case_count': len(cases), 'payloads': {str(p.relative_to(PACKAGE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in PACKAGE.rglob('*') if p.is_file()}}, indent=2)+'\n')
print(json.dumps({'cases': len(cases), 'executable_exists': (PACKAGE/'tools'/f'{ID}.py').exists()}))
