"""Independent cases written from contract/schema before implementation inspection."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
cases = []


def request(text, paths=None, source='Source.md'):
    return {'record_type':'audit_wikilink_resolution_request/v1',
        'syntax_profile':'bounded_markdown_wikilinks/v1','source_path':source,
        'text':text,'note_paths':paths or ['Source.md','Note.md','Shown.md','Hidden.md']}


def add(name, text='', paths=None, source='Source.md', links=None, error=None, override=None, raw=None):
    value=request(text, paths, source)
    if override: value.update(override)
    row={'name':name,'input':value,'expected_exit':2 if error else 0,
        'expected_error':error,'expected_links':links if links is not None else []}
    if raw is not None: row['raw_hex']=raw.hex()
    cases.append(row)


def link(target='Note', paths=None, status='resolved', **extra):
    return {'target':target,'status':status,'candidate_paths':paths or (['Note.md'] if status=='resolved' else []),**extra}


add('duplicate_basename_includes_source_no_preferred_folder','[[Note]]', ['z/Note.md','a/Note.md'], 'z/Note.md',
    [link(paths=['a/Note.md','z/Note.md'],status='ambiguous')])
add('slash_is_vault_root_not_source_relative','[[a/Note]]', ['folder/Source.md','a/Note.md','folder/a/Note.md'], 'folder/Source.md', [link('a/Note',['a/Note.md'])])
add('slash_root_miss_does_not_try_relative','[[a/Note]]', ['folder/Source.md','folder/a/Note.md'], 'folder/Source.md', [link('a/Note',status='missing')])
add('fragment_only_is_current_note','[[#Section]]', links=[link('', ['Source.md'], fragment='Section', fragment_status='not_checked')])
add('fragment_after_label_is_label_text','[[Note|label#value]]',links=[link(display='label#value',fragment=None,fragment_status='absent')])
add('note_fragment_and_label','[[Note#^block|display]]',links=[link(fragment='^block',display='display',fragment_status='not_checked')])
add('single_optional_md_suffix','[[Note.md.md]]', ['Source.md','Note.md','Note.md.md'],links=[link('Note.md.md',['Note.md.md'])])
add('unicode_identity_not_normalized','[[é]] [[é]]', ['Source.md','é.md','é.md'],links=[link('é',['é.md']),link('é',['é.md'])])
add('case_sensitive_identity','[[note]]',links=[link('note',status='missing')])
add('percent_escape_is_literal','[[a%20b]]', ['Source.md','a%20b.md','a b.md'],links=[link('a%20b',['a%20b.md'])])
add('dotted_basename_is_not_attachment','![[asset.png]]', ['Source.md','asset.png.md'],links=[link('asset.png',['asset.png.md'],embedded=True,start=1,end=14)])
add('unicode_codepoint_positions','🙂x\r\né[[Note]]',links=[link(start=5,end=13,line=2,column=2)])
add('odd_escape_ignores_link',r'\[[Note]]')
add('even_escape_starts_link',r'\\[[Note]]',links=[link(start=2,end=10,embedded=False)])
add('escaped_embed_marker_is_not_embed',r'\![[Note]]',links=[link(start=2,end=10,embedded=False)])
add('long_fence_ignores_short_closer','````\n[[Hidden]]\n```\n[[Hidden]]\n````\n[[Shown]]',links=[link('Shown',['Shown.md'])])
add('tilde_fence_not_closed_by_backticks','~~~\n[[Hidden]]\n```\n[[Hidden]]\n~~~~\n[[Shown]]',links=[link('Shown',['Shown.md'])])
add('three_space_fence_is_active','   ```py\n[[Hidden]]\n   ```\n[[Shown]]',links=[link('Shown',['Shown.md'])])
add('fence_closer_cannot_have_text','```\n[[Hidden]]\n``` text\n[[Hidden]]\n```\n[[Shown]]',links=[link('Shown',['Shown.md'])])
add('unclosed_fence_masks_eof','~~~\n[[Hidden]]')
add('indented_code_masks_each_line_only','    [[Hidden]]\n\t[[Hidden]]\n[[Shown]]',links=[link('Shown',['Shown.md'])])
add('paired_exact_backtick_runs','``[[Hidden]] ` text`` [[Shown]]',links=[link('Shown',['Shown.md'])])
add('unmatched_backtick_stays_literal','` [[Shown]]',links=[link('Shown',['Shown.md'])])
add('mismatched_backtick_runs_are_not_a_pair','`` [[Shown]] `',links=[link('Shown',['Shown.md'])])
add('multiline_inline_spans_outside_profile','`one\n[[Shown]]\n`',links=[link('Shown',['Shown.md'])])
add('html_comment_masks_links','<!-- [[Hidden]]\n[[Hidden]] --> [[Shown]]',links=[link('Shown',['Shown.md'])])
add('obsidian_comment_masks_links','%% [[Hidden]]\n[[Hidden]] %% [[Shown]]',links=[link('Shown',['Shown.md'])])
add('unclosed_html_comment_masks_eof','[[Shown]] <!-- [[Hidden]]',links=[link('Shown',['Shown.md'])])
add('frontmatter_exact_first_line','---\nkey: [[Hidden]]\n...\n[[Shown]]',links=[link('Shown',['Shown.md'])])
add('later_frontmatter_marker_is_literal','prefix\n---\n[[Shown]]\n---',links=[link('Shown',['Shown.md'])])
add('unclosed_frontmatter_refuses','---\n[[Hidden]]',error='unclosed_frontmatter')
for name,text in [('nested','[[a [[Note]]'),('unclosed','[[Note'),('multiple_pipes','[[Note|x|y]]'),('blank_label','[[Note|]]'),('blank_fragment','[[Note#]]'),('blank_target','[[]]'),('parent_target','[[../Note]]'),('leading_target_space','[[ Note]]')]:
    add('unsupported_'+name,text,links=[{'status':'unsupported','candidate_paths':[]}])
add('max_links_exact', ' '.join(['[[Note]]']*256),links=[link() for _ in range(256)])
add('link_count_over_limit', ' '.join(['[[Note]]']*257),error='link_limit_exceeded')
text='[[Note]]';h=hashlib.sha256(text.encode()).hexdigest()
add('matching_digest',text,links=[link()],override={'expected_sha256':h})
add('stale_digest',text,error='source_digest_mismatch',override={'expected_sha256':'0'*64})
add('unknown_request_field',error='invalid_input',override={'unexpected':True})
add('unknown_syntax_profile',error='invalid_input',override={'syntax_profile':'bounded_markdown_wikilinks/v2'})
add('source_not_in_inventory',paths=['Note.md'],error='invalid_input')
add('parent_inventory_path',paths=['Source.md','a/../Note.md'],error='invalid_input')
add('whitespace_inventory_segment',paths=['Source.md','a /Note.md'],error='invalid_input')
add('duplicate_inventory',paths=['Source.md','Source.md'],error='invalid_input')
add('unicode_input_wire_ceiling','🙂'*20000,error='invalid_input')
add('unicode_output_candidate_explosion',' '.join(['[[Note]]']*256),['Source.md']+[f'directory{i:03d}/Note.md' for i in range(255)],error='output_limit_exceeded')
base=request('');raw=json.dumps(base,separators=(',',':')).encode()
add('duplicate_json_key',error='invalid_input',raw=raw[:-1]+b',"text":""}')
add('nonfinite_json',error='invalid_input',raw=raw.replace(b'"text":""',b'"text":NaN'))
add('invalid_utf8',error='invalid_input',raw=raw.replace(b'"text":""',b'"text":"\xff"'))
add('unpaired_surrogate',error='invalid_input',raw=raw.replace(b'"text":""',b'"text":"\\ud800"'))
target=HERE/'wikilink-independent-before-source-1.json'
report={'record_type':'independent_wikilink_cases/v1','source_basis':'authors/wikilink-contract-before-code.md and two schemas; implementation not inspected',
    'contract_sha256':hashlib.sha256((ROOT/'authors/wikilink-contract-before-code.md').read_bytes()).hexdigest(),'cases':cases}
with target.open('x') as f:json.dump(report,f,indent=2,ensure_ascii=True);f.write('\n')
print(json.dumps({'cases':len(cases),'case_file':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
