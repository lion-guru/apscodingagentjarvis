/**
 * ═══════════════════════════════════════════════════
 *  Desktop Accessibility WORKER (out-of-process)
 * ═══════════════════════════════════════════════════
 *
 * Runs xa11y in a SEPARATE plain-Node process (forked with
 * ELECTRON_RUN_AS_NODE=1), NOT inside the Electron main process.
 *
 * WHY: on macOS the AppKit accessibility (AX) APIs must run on the main
 * thread when AppKit is initialised (i.e. inside an Electron GUI app). xa11y
 * runs its AX queries on a background worker pool, so calling it from the
 * Electron main process trips an AppKit assertion → SIGTRAP → the whole app
 * crashes. In a plain Node process (no AppKit run loop) the same calls are
 * fine. Isolating xa11y here also means a native crash only kills this helper,
 * never the main app.
 *
 * Protocol (over child_process IPC):
 *   parent → { id, cmd, args }
 *   worker → { id, result }   // result = { success, ... } | { success:false, error }
 */

let _xa11y = null;
function getXa11y() {
  if (!_xa11y) _xa11y = require('@crowecawcaw/xa11y');
  return _xa11y;
}

let _inputSim = null;
function getInputSim() {
  if (!_inputSim) _inputSim = getXa11y().inputSim();
  return _inputSim;
}

const SNAPSHOT_CHAR_LIMIT = 12000;

// The main process resolves the target (app name or pid) before sending, so
// the worker never needs AppleScript / platform-utils.
async function resolveApp(args) {
  const { App } = getXa11y();
  if (args && args._pid) {
    try {
      return await App.byPid(args._pid);
    } catch (_) {
      /* fall through to name */
    }
  }
  const name = args && args.app ? String(args.app).trim() : '';
  if (name) return await App.byName(name);
  throw new Error(
    "No target application. Call desktop_list_apps first, then pass the exact 'app' name."
  );
}

async function locatorFor(args) {
  const app = await resolveApp(args);
  const selector = args && args.selector ? String(args.selector) : '';
  if (!selector) {
    const err = new Error("A 'selector' is required for this action (e.g. \"button[name='Save']\").");
    err.code = 'INVALID_ARGS';
    throw err;
  }
  return app.locator(selector);
}

function describeElement(el) {
  return {
    role: el.role,
    name: el.name || null,
    value: el.value || null,
    enabled: el.enabled,
    visible: el.visible,
    focused: el.focused,
    checked: el.checked,
    selected: el.selected,
  };
}

const ok = (extra) => Object.assign({ success: true }, extra || {});
const fail = (error, code) => ({
  success: false,
  error: String(error && error.message ? error.message : error),
  code: code || undefined,
});

// ─── Command handlers ──────────────────────────────────────────────────────
const COMMANDS = {
  async 'list-apps'() {
    const { App } = getXa11y();
    const apps = await App.list();
    return ok({ apps: apps.map((a) => ({ name: a.name, pid: a.pid })).filter((a) => a.name) });
  },

  async snapshot(args) {
    const app = await resolveApp(args);
    const maxDepth = typeof args.maxDepth === 'number' ? args.maxDepth : null;
    let dump = args.selector
      ? await app.locator(String(args.selector)).dump(maxDepth)
      : await app.dump(maxDepth);
    let truncated = false;
    if (dump && dump.length > SNAPSHOT_CHAR_LIMIT) {
      dump = dump.slice(0, SNAPSHOT_CHAR_LIMIT);
      truncated = true;
    }
    return ok({ app: app.name, tree: dump, truncated });
  },

  async find(args) {
    const locator = await locatorFor(args);
    const els = await locator.elements();
    return ok({ count: els.length, elements: els.slice(0, 25).map(describeElement) });
  },

  async click(args) {
    await (await locatorFor(args)).press();
    return ok({ result: `Pressed ${args.selector}` });
  },

  async type(args) {
    const text = args.text == null ? '' : String(args.text);
    if (args.selector) {
      await (await locatorFor(args)).typeText(text);
    } else {
      await getInputSim().typeText(text);
    }
    return ok({ result: `Typed ${text.length} characters` });
  },

  async 'set-value'(args) {
    await (await locatorFor(args)).setValue(args.value == null ? '' : String(args.value));
    return ok({ result: `Set value of ${args.selector}` });
  },

  async toggle(args) {
    await (await locatorFor(args)).toggle();
    return ok({ result: `Toggled ${args.selector}` });
  },

  async select(args) {
    await (await locatorFor(args)).select();
    return ok({ result: `Selected ${args.selector}` });
  },

  async focus(args) {
    await (await locatorFor(args)).focus();
    return ok({ result: `Focused ${args.selector}` });
  },

  async key(args) {
    const key = args.key == null ? '' : String(args.key);
    if (!key) return fail("A 'key' is required.", 'INVALID_ARGS');
    const modifiers = Array.isArray(args.modifiers) ? args.modifiers.map(String) : [];
    const sim = getInputSim();
    if (modifiers.length > 0) await sim.chord(key, modifiers);
    else await sim.press(key);
    return ok({ result: `Pressed ${modifiers.concat(key).join('+')}` });
  },

  async wait(args) {
    const locator = await locatorFor(args);
    const state = (args.state || 'visible').toString();
    const timeoutSeconds = typeof args.timeoutSeconds === 'number' ? args.timeoutSeconds : 5;
    switch (state) {
      case 'attached': await locator.waitAttached(timeoutSeconds); break;
      case 'enabled': await locator.waitEnabled(timeoutSeconds); break;
      case 'hidden': await locator.waitHidden(timeoutSeconds); break;
      case 'focused': await locator.waitFocused(timeoutSeconds); break;
      default: await locator.waitVisible(timeoutSeconds); break;
    }
    return ok({ result: `${args.selector} reached state "${state}"` });
  },

  async permissions() {
    const { App } = getXa11y();
    const apps = await App.list();
    return ok({ granted: apps.length > 0, appCount: apps.length });
  },
};

process.on('message', async (msg) => {
  if (!msg || typeof msg !== 'object') return;
  const { id, cmd, args } = msg;
  let result;
  try {
    const handler = COMMANDS[cmd];
    result = handler ? await handler(args || {}) : fail(`Unknown command: ${cmd}`, 'INVALID_ARGS');
  } catch (err) {
    result = fail(err, err && err.code === 'INVALID_ARGS' ? 'INVALID_ARGS' : undefined);
  }
  try {
    process.send({ id, result });
  } catch (_) {
    /* parent gone */
  }
});

// Signal readiness so the parent knows the native module loaded.
try {
  process.send({ ready: true });
} catch (_) {}
