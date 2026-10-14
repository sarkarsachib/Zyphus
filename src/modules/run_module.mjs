/*
 * Loads one of the engine's own ES modules and reports what it exposes.
 *
 * The Python bridge (src/js_module_bridge_fixed.py) loads modules with require(),
 * which cannot read these `export class ...` files at all - that is why they were
 * unreachable. This runner uses a dynamic import(), so the agent's `js_module`
 * tool can actually open them, instantiate the class and list its methods.
 */
import { pathToFileURL } from 'url';
import path from 'path';
import fs from 'fs';

const target = process.argv[2];
if (!target) {
  console.log(JSON.stringify({ ok: false, error: 'no module path given' }));
  process.exit(2);
}

const absolute = path.resolve(target);
if (!fs.existsSync(absolute)) {
  console.log(JSON.stringify({ ok: false, error: `not found: ${absolute}` }));
  process.exit(2);
}

try {
  const module = await import(pathToFileURL(absolute).href);
  const exports = Object.keys(module);
  const instantiated = [];

  for (const [name, value] of Object.entries(module)) {
    if (typeof value !== 'function' || !/^[A-Z]/.test(name)) continue;
    try {
      const instance = new value();
      if (typeof instance.initialize === 'function') await instance.initialize();
      instantiated.push({
        class: name,
        methods: Object.getOwnPropertyNames(Object.getPrototypeOf(instance))
          .filter((key) => key !== 'constructor'),
      });
    } catch (error) {
      instantiated.push({ class: name, error: error.message });
    }
  }

  console.log(JSON.stringify({
    ok: true,
    module: path.relative(process.cwd(), absolute),
    exports,
    instantiated,
  }, null, 2));
} catch (error) {
  console.log(JSON.stringify({ ok: false, module: target, error: error.message }));
  process.exit(1);
}
