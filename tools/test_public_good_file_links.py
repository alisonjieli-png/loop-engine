"""File handoff selections are exact and do not grant authority or silently fall back."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PublicGoodFileLinks(unittest.TestCase):
    def test_exact_links_and_known_wrong_controls(self):
        node=shutil.which('node')
        self.assertIsNotNone(node,'Node is required for the browser selection check')
        script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context={window:{},URLSearchParams};vm.createContext(context);
vm.runInContext(fs.readFileSync('src/loop_engine/core/service_runtime/web_assets/catalogue-browser.js','utf8'),context);
const read=value=>context.window.BaltorCatalogueBrowser.fileSelection(value);
const good=new URLSearchParams({component:'public.example',file:'assets/tool/main.py',body_digest:'a'.repeat(64),file_digest:'b'.repeat(64)});
assert.equal(read('?component=public.example'),null);
const result=read(good.toString());assert.equal(result.path,'assets/tool/main.py');assert.equal(result.bodyDigest,'a'.repeat(64));
for(const bad of ['../secret','/absolute','assets//main.py','.git/config','%2e%2e/secret','assets/main.py\u0000',
 '.GIT/config',Array(9).fill('x').join('/'),'x'.repeat(101),'x'.repeat(100)+'/'+'y'.repeat(100)]){
 const changed=new URLSearchParams(good);changed.set('file',bad);assert.throws(()=>read(changed.toString()));
}
for(const name of ['file','body_digest','file_digest','component']){
 const missing=new URLSearchParams(good);missing.delete(name);assert.throws(()=>read(missing.toString()));
 const duplicate=new URLSearchParams(good);duplicate.append(name,duplicate.get(name));assert.throws(()=>read(duplicate.toString()));
}
const mismatch=new URLSearchParams(good);mismatch.set('file_digest','not-a-hash');assert.throws(()=>read(mismatch.toString()));
for(const path of ['.gitignore','x'.repeat(100)+'/'+'y'.repeat(99),Array(8).fill('x').join('/')]){
 const changed=new URLSearchParams(good);changed.set('file',path);assert.equal(read(changed.toString()).path,path);
}
console.log('exact file selection, three valid boundaries and 19 invalid/ambiguous controls passed');
'''
        result=subprocess.run([node,'-e',script],cwd=ROOT,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
