"""Exercise the actual feedback renderer with role, stale-response and private-text fixtures."""
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECK = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const full=fs.readFileSync('src/loop_engine/core/service_runtime/web_assets/service.js','utf8');
const start=full.indexOf('  let feedbackRequestNumber = 0;'),end=full.indexOf('  $("refresh-feedback").addEventListener',start);
assert(start>0&&end>start);
const code=full.slice(start,end);
const summary={record_type:'service_feedback_summary/v1',ratings:{useful:2,not_useful:1,items_rated:2},material_requests:{total:3,open:3},search_gaps:{groups:4,searches:5}};
const privateView={record_type:'service_feedback_view/v1',ratings:{useful:2,not_useful:1,items:[{item_identity:'item',useful:2,not_useful:1,notes:['PRIVATE_NOTE']}]},material_requests:[{description:'PRIVATE_REQUEST',tenant_id:'PRIVATE_ACCOUNT',at:1,state:'open'}],search_gaps:[]};
function fixture(role='analytics',scopes=[]){
 const nodes={},paths=[];
 const $=id=>nodes[id]??=( {hidden:true,children:[],replaceChildren(){this.children=[];this.rows=[];},append(value){this.children.push(value);}} );
 const context=vm.createContext({$,nodes,paths,initialRole:role,initialScopes:scopes,
  element:(tag,text)=>({tag,text,children:[],append(...parts){this.children.push(...parts);}}),
  tiles:(node,rows)=>{node.rows=rows;},message:(id,text)=>{$(id).text=text;},when:()=> 'synthetic date',
  request:async path=>{paths.push(path);return path.endsWith('/summary')?summary:privateView;}});
 vm.runInContext('let generation=1,staffRole=initialRole,principalScopes=initialScopes;'+code,context);
 return context;
}
(async()=>{
 let f=fixture();await f.loadFeedback();
 assert.deepEqual(f.paths,['/api/v1/admin/feedback/summary']);
 assert.equal(f.nodes['feedback-counts'].rows.length,5);assert(!JSON.stringify(f.nodes).includes('PRIVATE_'));
 for(const [role,scopes] of [['superadmin',[]],['',['access:manage']]]){
  f=fixture(role,scopes);await f.loadFeedback();assert.deepEqual(f.paths,['/api/v1/admin/feedback']);
  assert(JSON.stringify(f.nodes).includes('PRIVATE_REQUEST'));
 }
 f=fixture();f.request=async()=>privateView;
 await assert.rejects(f.loadFeedback(),/Feedback counts/);assert(!JSON.stringify(f.nodes).includes('PRIVATE_'));
 f=fixture();f.request=async()=>({...summary,ratings:{...summary.ratings,useful:true}});
 await assert.rejects(f.loadFeedback(),/Feedback counts/);
 f=fixture('superadmin');await f.loadFeedback();f.request=async()=>{throw Error('permission refused');};
 await assert.rejects(f.loadFeedback(),/permission refused/);assert(!JSON.stringify(f.nodes).includes('PRIVATE_'));
 f=fixture('superadmin');let finish;f.request=()=>new Promise(resolve=>{finish=resolve;});
 let task=f.loadFeedback();vm.runInContext('generation++;',f);finish(privateView);await task;
 assert(!JSON.stringify(f.nodes).includes('PRIVATE_'));
 f=fixture();const replies=[];f.request=()=>new Promise(resolve=>replies.push(resolve));
 const first=f.loadFeedback(),second=f.loadFeedback();replies[1](summary);await second;
 replies[0]({...summary,ratings:{...summary.ratings,useful:99}});await first;
 assert.equal(f.nodes['feedback-counts'].rows[0][1],'2');
 console.log('8 feedback UI controls passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''


class FeedbackBrowserTests(unittest.TestCase):
    def test_actual_renderer_keeps_analytics_and_stale_responses_private(self):
        result = subprocess.run(["node", "-e", CHECK], cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("8 feedback UI controls passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
