/**
 * ═══════════════════════════════════════════════════
 *  Desktop Accessibility Service (Backend, proxy)
 * ═══════════════════════════════════════════════════
 *
 * Gives the Voice Assistant a "screen-reader" style control layer over ANY
 * native application — the OS accessibility tree (AX / UI Automation /
 * AT-SPI) that screen readers expose to blind users. The AI reads a compact
 * STRUCTURED TEXT snapshot of an app (roles + names, not pixels) and acts on
 * elements via CSS-like selectors. No screenshots, no pixel guessing.
 *
 * Built on @crowecawcaw/xa11y. IMPORTANT: xa11y runs its accessibility queries
 * on background worker threads, and on macOS AppKit forbids that inside a GUI
 * (Electron) process — it SIGTRAPs the whole app. So we do NOT call xa11y in
 * the Electron main process. Instead this module forks a plain-Node worker
 * (desktop-ax-worker.js, ELECTRON_RUN_AS_NODE) and proxies every request to it
 * over IPC. That fixes the threading crash AND isolates any native crash from
 * the main app.
 *
 * Channels are namespaced `desktop-ax-*` to avoid colliding with the older
 * robotjs `desktop-*` handlers in desktop-manager.js.
 *
 * macOS requires Accessibility permission (and Screen Recording for some
 * apps) — bootstrapped in macos-permissions.js.
 */

const { ipcMain } = require('electron');
const path = require('path');
const { fork } = require('child_process');
const { isMac, macGetActiveWindow } = require('./platform-utils');

const WORKER_PATH = path.join(__dirname, 'desktop-ax-worker.js');
const REQUEST_TIMEOUT_MS = 30000;

let child = null;
let nextId = 1;
const pending = new Map(); // id → { resolve, timer }

function killChild(err) {
  if (child) {
    try { child.removeAllListeners(); } catch (_) {}
    try { child.kill(); } catch (_) {}
    child = null;
  }
  // Reject anything still in flight so callers don't hang.
  for (const [, p] of pending) {
    clearTimeout(p.timer);
    p.resolve({ success: false, error: err || 'Desktop accessibility worker stopped.' });
  }
  pending.clear();
}

function ensureChild() {
  if (child) return child;

  child = fork(WORKER_PATH, [], {
    // ELECTRON_RUN_AS_NODE makes the Electron binary run as a plain Node
    // process (no AppKit), which is where xa11y's AX worker threads are safe.
    env: Object.assign({}, process.env, { ELECTRON_RUN_AS_NODE: '1' }),
    stdio: ['ignore', 'inherit', 'inherit', 'ipc'],
  });

  child.on('message', (msg) => {
    if (!msg || typeof msg !== 'object') return;
    if (msg.ready) return; // readiness ping
    const p = pending.get(msg.id);
    if (!p) return;
    pending.delete(msg.id);
    clearTimeout(p.timer);
    p.resolve(msg.result);
  });

  child.on('exit', (code, signal) => {
    killChild(`Desktop accessibility worker exited (code=${code}, signal=${signal}).`);
  });
  child.on('error', (e) => {
    killChild(`Desktop accessibility worker error: ${e && e.message}`);
  });

  return child;
}

function callWorker(cmd, args) {
  return new Promise((resolve) => {
    let proc;
    try {
      proc = ensureChild();
    } catch (e) {
      resolve({ success: false, error: `Failed to start desktop worker: ${e && e.message}` });
      return;
    }

    const id = nextId++;
    const timer = setTimeout(() => {
      pending.delete(id);
      resolve({ success: false, error: `Desktop action "${cmd}" timed out.` });
    }, REQUEST_TIMEOUT_MS);

    pending.set(id, { resolve, timer });
    try {
      proc.send({ id, cmd, args: args || {} });
    } catch (e) {
      pending.delete(id);
      clearTimeout(timer);
      resolve({ success: false, error: `Failed to reach desktop worker: ${e && e.message}` });
    }
  });
}

/**
 * Resolve the target application in the MAIN process (the worker is kept pure
 * xa11y). If the caller gave `app`, pass it through. Otherwise fall back to the
 * frontmost app (macOS only) and pass its pid so the worker can use byPid.
 */
async function withResolvedTarget(args) {
  const out = Object.assign({}, args || {});
  if (out.app && String(out.app).trim()) return out;

  if (isMac && typeof macGetActiveWindow === 'function') {
    try {
      const info = await macGetActiveWindow();
      if (info && info.pid) out._pid = info.pid;
      if (info && info.processName) out.app = info.processName;
    } catch (_) {
      /* worker will return a helpful "no target" error */
    }
  }
  return out;
}

function registerDesktopAccessibilityHandlers() {
  // Commands that don't need a target app.
  ipcMain.handle('desktop-ax-list-apps', async () => callWorker('list-apps'));
  ipcMain.handle('desktop-ax-permissions', async () => callWorker('permissions'));

  // Commands that act on an app — resolve the target first.
  const targeted = {
    'desktop-ax-snapshot': 'snapshot',
    'desktop-ax-find': 'find',
    'desktop-ax-click': 'click',
    'desktop-ax-type': 'type',
    'desktop-ax-set-value': 'set-value',
    'desktop-ax-toggle': 'toggle',
    'desktop-ax-select': 'select',
    'desktop-ax-focus': 'focus',
    'desktop-ax-wait': 'wait',
  };
  for (const [channel, cmd] of Object.entries(targeted)) {
    ipcMain.handle(channel, async (event, args = {}) => {
      const resolved = await withResolvedTarget(args);
      return callWorker(cmd, resolved);
    });
  }

  // Global keystroke — no app target needed (goes to the focused app).
  ipcMain.handle('desktop-ax-key', async (event, args = {}) => callWorker('key', args));
}

// The worker is the Electron binary itself (ELECTRON_RUN_AS_NODE), so in Task
// Manager — and to the NSIS updater's process check — it is another
// "Stonic AI.exe". Quit paths must be able to take it down explicitly.
function stopDesktopAccessibilityWorker() {
  killChild('App is shutting down.');
}

module.exports = { registerDesktopAccessibilityHandlers, stopDesktopAccessibilityWorker };
