// Decode five exact sample frames from each qualified cut into a PNG preview.
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import {resolve,dirname,isAbsolute} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const here=dirname(fileURLToPath(import.meta.url)),repository=resolve(here,'../../..'),[input,output]=process.argv.slice(2);
if(!input||!output||!isAbsolute(input)||!isAbsolute(output))throw Error('Use absolute qualified input and new output directories');
const report=JSON.parse(await readFile(resolve(input,'verification.json')));
if(report.record_type!=='baltor_launch_motion_export/v1'||report.passed!==true||report.videos.length!==6)throw Error('Expected the complete qualified six-cut record');
const require=createRequire(import.meta.url),ffmpeg=require(resolve(process.env.BALTOR_SHOWCASE_MODULES||resolve(repository,'showcase/node_modules'),'ffmpeg-static'));
await mkdir(output);const rows=[];
for(const video of report.videos){
 if(!/^(?:2d|2p5d|3d)-(?:landscape|portrait)\.mp4$/.test(video.file))throw Error('Unknown cut filename');
 const source=resolve(input,video.file),bytes=await readFile(source),hash=body=>createHash('sha256').update(body).digest('hex');if(hash(bytes)!==video.sha256)throw Error('Video changed');
 const name=video.file.replace('.mp4','.png'),portrait=video.height>video.width;
 const filter="select='eq(n,24)+eq(n,192)+eq(n,360)+eq(n,528)+eq(n,672)',scale="+(portrait?'216:384':'384:216')+',tile=5x1';
 const result=spawnSync(ffmpeg,['-v','error','-n','-i',source,'-vf',filter,'-frames:v','1',resolve(output,name)],{encoding:'utf8'});if(result.status!==0)throw Error(result.stderr);
 const image=await readFile(resolve(output,name));rows.push({file:name,bytes:image.length,sha256:hash(image),video_sha256:video.sha256,frame_indices:[24,192,360,528,672]});
}
await writeFile(resolve(output,'previews.json'),JSON.stringify({record_type:'launch_motion_preview_set/v1',rows},null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({previews:rows.length,output}));
