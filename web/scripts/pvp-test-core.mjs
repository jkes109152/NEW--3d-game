import { readFile } from 'node:fs/promises';
import { loadPyodide } from 'pyodide';
import { createRequire } from 'node:module';
import { dirname } from 'node:path';
export async function testCore() {
  const py = await loadPyodide({
    indexURL: dirname(createRequire(import.meta.url).resolve('pyodide')),
  });
  py.FS.mkdirTree('/home/pyodide/air_defense');
  for (const name of JSON.parse(
    await readFile('public/rules/manifest.json', 'utf8'),
  ))
    py.FS.writeFile(
      `/home/pyodide/air_defense/${name}.py`,
      await readFile(`public/rules/${name}.py`, 'utf8'),
    );
  py.runPython(await readFile('public/bridge.py', 'utf8'));
  return {
    py,
    invoke(name, value = {}) {
      const fn = py.globals.get(name);
      try {
        return JSON.parse(fn(JSON.stringify(value)));
      } finally {
        fn.destroy();
      }
    },
  };
}
