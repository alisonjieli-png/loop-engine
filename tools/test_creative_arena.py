"""The creative example must be packaged completely and stay outside account framing."""
import hashlib
import json
from pathlib import Path
import unittest

from loop_engine.core.service_runtime.web_pages import served_asset
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'src/loop_engine/core/service_runtime/web_assets/creative-arena'


class CreativeArenaChecks(unittest.TestCase):
    def test_build_binds_current_sources_and_every_packaged_file(self):
        manifest=json.loads((ASSETS/'build.json').read_text())
        self.assertEqual(manifest['record_type'],'creative_arena_build/v1')
        for path,digest in manifest['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ASSETS/name).read_bytes()).hexdigest(),digest,name)

    def test_page_and_native_material_have_explicit_routes(self):
        for path in ('/demo/ashen-wilds','/assets/creative-arena/index.html',
                     '/assets/creative-arena/arena.js','/assets/creative-arena/arena.css',
                     '/assets/creative-arena/asset-briefs.json','/assets/creative-arena/blender-import.py',
                     '/assets/creative-arena/THREE-LICENSE.txt'):
            answer=served_asset(path,'GET','Baltor')
            self.assertIsNotNone(answer,path)
            self.assertTrue(answer[0],path)
        self.assertIn(b'data-view="creative-arena"',served_asset('/demo/ashen-wilds','GET','Baltor')[0])

    def test_preview_names_exact_cached_script_and_style_versions(self):
        page = served_asset('/assets/creative-arena/index.html', 'GET', 'Baltor')[0]
        for name in ('arena.js', 'arena.css'):
            digest = hashlib.sha256((ASSETS/name).read_bytes()).hexdigest()
            self.assertIn(f'/assets/creative-arena/{name}?v={digest}"'.encode(), page)
            self.assertNotIn(f'/assets/creative-arena/{name}"'.encode(), page)

    def test_only_the_explicit_preview_profile_accepts_same_origin_framing(self):
        import tempfile
        import httpx
        with tempfile.TemporaryDirectory() as directory:
            fixture=HttpDomainFixture(Path(directory))
            with running_http(fixture) as (base,_application), httpx.Client(base_url=base,trust_env=False) as client:
                ordinary=client.get('/app')
                preview=client.get('/assets/creative-arena/index.html')
                other=client.get('/assets/service.js?creative_preview=true')
                self.assertEqual((ordinary.status_code,preview.status_code,other.status_code),(200,200,200))
                self.assertEqual(ordinary.headers['X-Frame-Options'],'DENY')
                self.assertIn("frame-ancestors 'none'",ordinary.headers['Content-Security-Policy'])
                self.assertEqual(preview.headers['X-Frame-Options'],'SAMEORIGIN')
                self.assertIn("frame-ancestors 'self'",preview.headers['Content-Security-Policy'])
                self.assertNotIn('https://',preview.headers['Content-Security-Policy'])
                self.assertEqual(other.headers['X-Frame-Options'],'DENY')


if __name__=='__main__':unittest.main()
