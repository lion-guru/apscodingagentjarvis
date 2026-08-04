const { ipcMain } = require('electron');
const path = require('path');
const { pathToFileURL } = require('url');
const { WhatsAppPairing } = require('../../services/whatsapp-pairing');

// IPC surface for the embedded (but unmodified) Hermes Agent dashboard.
// The renderer never talks to Hermes directly for REST — everything goes
// through HermesManager so the session token stays in the main process.
function registerHermesHandlers({ getHermesManager }) {
  // One pairing controller for the app's lifetime: it holds the running
  // bridge process, so a second instance could orphan the first.
  let pairing = null;
  const getPairing = () => {
    const mgr = getHermesManager();
    if (!mgr) return null;
    if (!pairing) pairing = new WhatsAppPairing(mgr);
    return pairing;
  };
  ipcMain.handle('hermes:get-state', () => {
    const mgr = getHermesManager();
    return mgr ? mgr.getState() : { state: 'idle', url: null, status: null };
  });

  ipcMain.handle('hermes:start', async () => {
    const mgr = getHermesManager();
    if (!mgr) return { state: 'error', error: 'Hermes manager not initialised' };
    return mgr.start();
  });

  // Writing an env var (an API key, from any Settings panel) changes something
  // a RUNNING gateway can never observe — see
  // HermesManager.restartGatewayForCredentialChange() for why. Detecting it here
  // rather than in each Settings panel means a panel added later cannot forget
  // it, and it deliberately does NOT sit inside apiFetch: the WhatsApp pairing
  // flow writes env through the manager directly and already does its own,
  // better-sequenced bounce.
  const isEnvWrite = (apiPath, method) =>
    String(apiPath || '').startsWith('/api/env') &&
    ['PUT', 'POST', 'PATCH', 'DELETE'].includes(String(method || 'GET').toUpperCase());

  ipcMain.handle('hermes:api', async (_event, apiPath, options) => {
    const mgr = getHermesManager();
    if (!mgr) return { ok: false, status: 0, data: { error: 'Hermes manager not initialised' } };
    const res = await mgr.apiFetch(apiPath, options || {});
    if (res.ok && isEnvWrite(apiPath, options && options.method)) {
      // Awaited so the renderer's "saved" message only lands once the gateway is
      // actually being restarted; never allowed to fail the save itself.
      try {
        await mgr.restartGatewayForCredentialChange();
      } catch (err) {
        console.warn('[Hermes] Credential-change gateway bounce failed:', err.message);
      }
    }
    return res;
  });

  // Connection info for the renderer's chat WebSocket (Expert Agent chat).
  // Hermes' chat gateway streams over ws://…/api/ws?token=… — the renderer
  // opens that socket itself and re-requests this on every (re)connect so a
  // rotated session token is always current.
  ipcMain.handle('hermes:get-connection', async () => {
    const mgr = getHermesManager();
    if (!mgr) return { ok: false, baseUrl: null, wsUrl: null, token: null, state: 'idle' };
    return mgr.getConnectionInfo();
  });

  // Read-only: Hermes' curated memory files (MEMORY.md + USER.md) for
  // injection into the voice assistant's system prompt. Never writes.
  ipcMain.handle('hermes:memory-read', () => {
    const mgr = getHermesManager();
    if (!mgr) return { available: false, memory: '', user: '' };
    return mgr.readMemoryFiles();
  });

  // Write path: queue a fact for Hermes to evaluate and (maybe) store via
  // its OWN memory tool — Stonic never writes Hermes' files itself.
  ipcMain.handle('hermes:share-fact', (_event, payload) => {
    const mgr = getHermesManager();
    if (!mgr) return { ok: false, error: 'Hermes manager not initialised' };
    const { fact, person } = payload || {};
    return mgr.shareFact(fact, person);
  });

  // Interactive memory edit from the Memory modal: a plain-language request
  // ("add X", "fix Y", "forget Z") handed to Hermes' agent. Awaited so the
  // modal can show the result and re-read the (Hermes-written) files.
  ipcMain.handle('hermes:memory-request', async (_event, payload) => {
    const mgr = getHermesManager();
    if (!mgr) return { ok: false, error: 'Hermes manager not initialised' };
    const { instruction } = payload || {};
    return mgr.memoryRequest(instruction);
  });

  // ── WhatsApp pairing (see services/whatsapp-pairing.js) ────────────────
  // Hermes' `hermes whatsapp` command is interactive and prints its QR to a
  // terminal the packaged app does not have. We run the same bridge script it
  // runs and stream the QR to a Stonic modal over `hermes-whatsapp-pair`.

  ipcMain.handle('hermes:whatsapp-pair-info', async () => {
    const wa = getPairing();
    if (!wa) return { ok: false, error: 'Hermes manager not initialised' };
    try {
      return await wa.info();
    } catch (err) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle('hermes:whatsapp-pair-start', async (_event, options) => {
    const wa = getPairing();
    if (!wa) return { ok: false, error: 'Hermes manager not initialised' };
    // Resolves only when pairing settles; progress arrives as events.
    return wa.start({ force: !!(options && options.force) });
  });

  ipcMain.handle('hermes:whatsapp-pair-cancel', () => {
    const wa = getPairing();
    if (!wa) return { ok: false, error: 'Hermes manager not initialised' };
    return wa.cancel();
  });

  // Backup for the number pairing normally reads out of the session itself.
  ipcMain.handle('hermes:whatsapp-set-phone', async (_event, options) => {
    const wa = getPairing();
    if (!wa) return { ok: false, error: 'Hermes manager not initialised' };
    return wa.setPhone(options && options.phone);
  });

  // Disables WhatsApp and destroys the local session. The linked device must
  // still be removed on the phone — the bridge has no logout call.
  ipcMain.handle('hermes:whatsapp-unlink', async () => {
    const wa = getPairing();
    if (!wa) return { ok: false, error: 'Hermes manager not initialised' };
    return wa.unlink();
  });

  // Guest preload for the dashboard <webview>: lets the injected "Set up with
  // QR" button on Hermes' Channels page call back into Stonic.
  ipcMain.handle('hermes:get-preload-path', () => {
    try {
      return pathToFileURL(path.join(__dirname, '..', '..', 'hermes-preload.js')).toString();
    } catch {
      return null;
    }
  });
}

module.exports = { registerHermesHandlers };
