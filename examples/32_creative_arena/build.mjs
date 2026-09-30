import {build} from 'esbuild';
import {mkdir, copyFile} from 'node:fs/promises';

await mkdir('dist', {recursive: true});
await build({entryPoints: ['src/game.mjs'], bundle: true, format: 'esm',
  outfile: 'dist/arena.js', target: ['es2022'], minify: true, legalComments: 'eof'});
for (const file of ['index.html', 'arena.css', 'asset-briefs.json', 'blender-import.py']) {
  await copyFile(file, `dist/${file}`);
}
await copyFile('node_modules/three/LICENSE', 'dist/THREE-LICENSE.txt');
