"""Package the original browser example into the existing Baltor website.

The pinned npm lock builds Three.js locally. No CDN or remote asset is needed
at runtime. --check compares an existing build with the packaged view.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'examples/32_creative_arena'
TARGET=ROOT/'src/loop_engine/core/service_runtime/web_assets/creative-arena'
FILES={'index.html':'index.html','arena.css':'arena.css','arena.js':'arena.js',
       'asset-briefs.json':'asset-briefs.json','blender-import.py':'blender-import.py.txt',
       'THREE-LICENSE.txt':'THREE-LICENSE.txt'}


def packaged_files():
    result={}
    for name,target in FILES.items():
        body=(SOURCE/'dist'/name).read_bytes()
        if name=='index.html':
            body=body.replace(b'href="./',b'href="/assets/creative-arena/').replace(b'src="./',b'src="/assets/creative-arena/')
            body=body.replace(b'href="data:,"',b'href="/assets/favicon-32.png"')
            for asset in ('arena.js', 'arena.css'):
                version = hashlib.sha256((SOURCE/'dist'/asset).read_bytes()).hexdigest()
                plain = ('/assets/creative-arena/' + asset).encode()
                body = body.replace(plain + b'"', plain + b'?v=' + version.encode() + b'"')
        result[target]=body
    sources=[SOURCE/'package.json',SOURCE/'package-lock.json',SOURCE/'build.mjs',SOURCE/'index.html',
             SOURCE/'arena.css',SOURCE/'asset-briefs.json',SOURCE/'blender-import.py',*sorted((SOURCE/'src').glob('*.mjs'))]
    manifest={'record_type':'creative_arena_build/v1',
              'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              'files':{name:hashlib.sha256(body).hexdigest() for name,body in sorted(result.items())}}
    result['build.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--build',action='store_true')
    args=parser.parse_args()
    if args.build:
        subprocess.run(['npm','run','build'],cwd=SOURCE,check=True)
    expected=packaged_files()
    if args.check:
        wrong=[name for name,body in expected.items() if not (TARGET/name).is_file() or (TARGET/name).read_bytes()!=body]
        if wrong:raise SystemExit('Creative example build differs: '+', '.join(wrong))
    else:
        TARGET.mkdir(parents=True,exist_ok=True)
        for name,body in expected.items():(TARGET/name).write_bytes(body)
    print(json.dumps({'files':len(expected),'check':args.check,'bytes':sum(map(len,expected.values()))}))


if __name__=='__main__':main()
