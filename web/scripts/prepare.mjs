import {mkdir,copyFile,writeFile,cp,access} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const modules=['__init__','config','catalog','combat','deployment','entities','loadout','preparation','progression','projectiles','save_data','state','multiplayer','weapons','visual_catalog'];
await mkdir(root+'public/rules',{recursive:true});
let desktop=false;try{await access(root+'../air_defense/state.py');desktop=true}catch{}
if(desktop)for(const name of modules) await copyFile(root+'../air_defense/'+name+'.py',root+'public/rules/'+name+'.py');
await writeFile(root+'public/rules/manifest.json',JSON.stringify(modules));
await mkdir(root+'public/runtime',{recursive:true});
for(const name of ['pyodide.js','pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json']) await copyFile(root+'node_modules/pyodide/'+name,root+'public/runtime/'+name);
if(desktop){await cp(root+'../assets/audio',root+'public/audio',{recursive:true});await cp(root+'../assets/textures',root+'public/textures',{recursive:true})}
console.log('遊戲規則、執行環境與音效已準備完成。');
