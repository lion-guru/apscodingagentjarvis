// HermesManager — runs the UNMODIFIED Hermes Agent dashboard as a separate
// local process and gives Stonic a narrow, read-mostly bridge to it.
//
// Hard rule (see user directive): the Hermes install is never patched or
// reconfigured from here. We only (1) spawn the same `hermes dashboard
// --no-open` command the user runs by hand, (2) probe its public
// /api/status endpoint, and (3) forward REST calls with the session token
// the dashboard itself injects into its index.html.
//
// If a dashboard is already running on the port (user started it manually),
// we adopt it instead of spawning a second one and we never kill it on exit.

const { spawn } = require('child_process');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');
const os = require('os');
const axios = require('axios');
const { resolveHermesExe, hermesSpawnEnv } = require('./hermes-runtime');
const childRegistry = require('./child-registry');

const DEFAULT_PORT = parseInt(process.env.STONIC_HERMES_PORT || '9119', 10);
// First boot can rebuild the dashboard web bundle (npm build inside Hermes),
// which takes minutes on slow disks. Poll generously.
const READY_TIMEOUT_MS = 4 * 60 * 1000;
const READY_POLL_MS = 1500;
const STATUS_REFRESH_MS = 15000;
// Quit is not the place to wait out a slow gateway shutdown; main.js' sync sweep
// kills whatever is still standing after this.
const GATEWAY_STOP_TIMEOUT_MS = 4000;
// Recording owned processes costs a full process scan, so the status loop is
// rate-limited to this. Gateway start and shutdown bypass it.
const OWNED_SCAN_MIN_INTERVAL_MS = 60 * 1000;
// How long an agent turn may go with NO activity at all before Hermes cuts it
// loose — see _ensureGatewayTimeout(). Hermes' own default is the value we only
// overwrite when we find it unchanged.
const HERMES_DEFAULT_GATEWAY_TIMEOUT = 1800;
const STUCK_TURN_TIMEOUT_S = 600;
const STUCK_TURN_WARNING_S = 300;
// Hermes' api_server platform — the OpenAI-compatible HTTP surface that also
// carries its asynchronous run API (/v1/runs). Agent Town drives its seats
// through it; see agent-town-main/lib/hermes-run-api.ts.
const RUN_API_PORT = parseInt(process.env.STONIC_HERMES_API_PORT || '8642', 10);

class HermesManager {
  constructor() {
    this.port = DEFAULT_PORT;
    this.baseUrl = `http://127.0.0.1:${this.port}`;
    this.child = null;
    this.external = false;        // true when we adopted a dashboard we did not spawn
    this.state = 'idle';          // idle | starting | ready | error | stopped
    this.error = null;
    this.token = null;
    this.lastStatus = null;       // last /api/status payload
    this.exePath = null;
    this.mainWindow = null;
    this._readyPoller = null;
    this._statusTimer = null;
    this._stopping = false;
    this._autoRestarts = 0;   // crash-loop guard for spawned children
    // Gateway + WhatsApp bridge are siblings, not children — see child-registry.
    // The snapshot is every such process that existed BEFORE we did anything,
    // so whatever appears later is ours to clean up and the user's own Hermes
    // never is.
    this._preexistingHermes = [];
    this._gatewayStartedByUs = false;
    this._approvalBypassApplied = false;
    this._sttProviderApplied = false;
    this._gatewayTimeoutApplied = false;
    // { url, key } for Hermes' run API once api_server is configured.
    this.runApi = null;
    this._runApiPromise = null;
    this._runApiVerifiedAt = 0;
    this._runApiFailedAt = 0;
  }

  setWindow(win) { this.mainWindow = win; }

  // ── Read-only personalization bridge ─────────────────────────────────
  // Hermes' data home (Windows: %LOCALAPPDATA%\hermes, elsewhere ~/.hermes).
  // Stonic only ever READS the memory files here — it never creates, writes,
  // or locks anything inside this folder (see the hard rule at the top).
  getHermesHome() {
    if (process.platform === 'win32') {
      const localAppData = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
      return path.join(localAppData, 'hermes');
    }
    return path.join(os.homedir(), '.hermes');
  }

  // Read Hermes' curated memory (MEMORY.md + USER.md) so the voice assistant
  // can inject it into its system prompt at session start — the same frozen
  // snapshot pattern Hermes itself uses. Files are UTF-8 with § delimiters;
  // reading them has zero effect on Hermes.
  readMemoryFiles() {
    const memoriesDir = path.join(this.getHermesHome(), 'memories');
    const readOne = (name) => {
      try {
        const p = path.join(memoriesDir, name);
        if (!fs.existsSync(p)) return '';
        return fs.readFileSync(p, 'utf8').trim();
      } catch (err) {
        console.warn(`[Hermes] Could not read ${name}:`, err.message);
        return '';
      }
    };
    const memory = readOne('MEMORY.md');
    const user = readOne('USER.md');
    return {
      available: Boolean(memory || user),
      memory,
      user,
      home: this.getHermesHome(),
    };
  }

  // ── Write path: hand a fact to Hermes so HERMES decides and writes ──
  // Stonic never touches Hermes' memory files. A fact is delivered as a
  // one-shot agent run (`hermes -z "<prompt>"`): Hermes' own agent evaluates
  // it against its save/skip policy and, if worth keeping, stores it via its
  // own memory tool — so char limits, security scanning, dedup and (if
  // enabled) write approval all stay enforced. Facts are queued and run one
  // at a time; results are logged and broadcast, never awaited by the voice
  // turn.
  shareFact(fact, person) {
    const cleanFact = String(fact || '').trim().slice(0, 600);
    if (!cleanFact) return { ok: false, error: 'Empty fact' };
    if (!this._shareQueue) this._shareQueue = [];
    this._shareQueue.push({ fact: cleanFact, person: String(person || '').trim().slice(0, 80) });
    this._drainShareQueue();
    return { ok: true, queued: true, pending: this._shareQueue.length };
  }

  _drainShareQueue() {
    if (this._shareBusy || !this._shareQueue || this._shareQueue.length === 0) return;
    this._shareBusy = true;
    const { fact, person } = this._shareQueue.shift();

    // Light touch, same as memoryRequest: relay the fact and let Hermes apply
    // its own memory policy. The only thing Hermes can't infer is WHO the fact
    // is about when it's not the owner, so we pass that as plain context — not
    // as an instruction on how to store it.
    const context = person
      ? `The user mentioned something about ${person} (not the owner): "${fact}".`
      : `The user mentioned: "${fact}".`;
    const prompt =
      `[Memory note via Stonic voice assistant] ${context} ` +
      "Please save it to their memory if it's worth keeping.";

    const exe = this.resolveExe();
    console.log('[Hermes] Memory hand-off via oneshot:', fact.slice(0, 120));
    let child;
    try {
      child = spawn(exe, ['-z', prompt], {
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
        cwd: os.homedir(),
        env: hermesSpawnEnv(),
      });
    } catch (err) {
      this._finishShare(fact, false, `spawn failed: ${err.message}`);
      return;
    }

    let out = '';
    let settled = false;
    const settle = (ok, message) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      this._finishShare(fact, ok, message);
    };
    // First runs can be slow (venv warm-up + model call) — allow 3 minutes.
    const timer = setTimeout(() => {
      try { child.kill(); } catch { /* already gone */ }
      settle(false, 'timed out after 180s');
    }, 180000);

    child.stdout?.on('data', (buf) => { out += String(buf); });
    child.stderr?.on('data', (buf) => { out += String(buf); });
    child.on('error', (err) => settle(false, `launch error: ${err.message} (is Hermes installed?)`));
    child.on('exit', (code) => {
      const summary = out.trim().split(/\r?\n/).filter(Boolean).pop() || '(no output)';
      settle(code === 0, code === 0 ? summary : `exit ${code}: ${summary.slice(0, 300)}`);
    });
  }

  // ── Interactive memory request (from the Memory modal) ──────────────
  // The user types a plain-language memory instruction ("add X", "fix the
  // entry that says Y", "forget Z"). We hand it to Hermes' OWN agent via a
  // one-shot; Hermes edits its memory with its own tool (limits, scanning,
  // dedup, approval gate all apply). Unlike shareFact this is AWAITED so the
  // modal can show the result and re-read the files. Never writes files here.
  async memoryRequest(instruction) {
    const clean = String(instruction || '').trim().slice(0, 1500);
    if (!clean) return { ok: false, error: 'Empty request' };

    // Light touch: just relay the user's request. Hermes already knows how to
    // manage its own memory (add/replace/remove, limits, curation) — we don't
    // instruct it, we only point that a memory request came in.
    const prompt =
      `[Memory request via Stonic app] The user said: "${clean}". ` +
      'Please save or update their memory accordingly.';

    const exe = this.resolveExe();
    console.log('[Hermes] Memory request via oneshot:', clean.slice(0, 120));

    return new Promise((resolve) => {
      let child;
      try {
        child = spawn(exe, ['-z', prompt], {
          windowsHide: true,
          stdio: ['ignore', 'pipe', 'pipe'],
          cwd: os.homedir(),
          env: hermesSpawnEnv(),
        });
      } catch (err) {
        return resolve({ ok: false, error: `Could not launch Hermes: ${err.message}` });
      }

      let out = '';
      let settled = false;
      const settle = (result) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(result);
      };
      const timer = setTimeout(() => {
        try { child.kill(); } catch { /* already gone */ }
        settle({ ok: false, error: 'Hermes took too long (over 180s) — try again.' });
      }, 180000);

      child.stdout?.on('data', (buf) => { out += String(buf); });
      child.stderr?.on('data', (buf) => { out += String(buf); });
      child.on('error', (err) => settle({ ok: false, error: `Hermes launch error: ${err.message} (is Hermes installed?)` }));
      child.on('exit', (code) => {
        const summary = out.trim().split(/\r?\n/).filter(Boolean).pop() || '(no response)';
        if (code === 0) {
          settle({ ok: true, message: summary });
        } else {
          settle({ ok: false, error: `Hermes exited (code ${code}): ${summary.slice(0, 300)}` });
        }
      });
    });
  }

  _finishShare(fact, ok, message) {
    console.log(`[Hermes] Memory hand-off ${ok ? 'done' : 'FAILED'}:`, message.slice(0, 300));
    try {
      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.webContents.send('hermes-share-result', { ok, fact, message });
      }
    } catch { /* window may be closing */ }
    this._shareBusy = false;
    // Keep draining queued facts sequentially.
    setTimeout(() => this._drainShareQueue(), 500);
  }

  // ── Public state consumed by the renderer ────────────────────────────
  getState() {
    return {
      state: this.state,
      error: this.error,
      url: this.baseUrl,
      port: this.port,
      external: this.external,
      exePath: this.exePath,
      status: this.lastStatus,
    };
  }

  _setState(state, error = null) {
    this.state = state;
    this.error = error;
    this._broadcast();
  }

  _broadcast() {
    try {
      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.webContents.send('hermes-state', this.getState());
      }
    } catch { /* window may be closing */ }
  }

  // ── Approval bypass that outlives our own spawns ─────────────────────
  // hermesSpawnEnv()'s HERMES_YOLO_MODE only reaches processes Stonic starts,
  // and two Hermes processes routinely escape that: a dashboard that was
  // already running when we booted (we adopt it rather than spawn one), and a
  // gateway Windows relaunches from its ONLOGON scheduled task. Both would go
  // back to blocking a turn on an approval nobody is watching for — the
  // WhatsApp path especially, where there is no UI to answer from.
  //
  // So once the dashboard answers, persist the same bypass as config. Hermes'
  // config cache is mtime-keyed, so this lands on the running processes too,
  // without a restart. PUT /api/config deep-merges server-side, so only these
  // four keys move and everything else the user has set survives.
  //
  // This writes user data (%LOCALAPPDATA%\hermes\config.yaml), the same place
  // _ensureStonicThemes() writes — the Hermes install itself stays untouched.
  async _ensureApprovalBypass() {
    if (this._approvalBypassApplied) return;
    const res = await this.apiFetch('/api/config', {
      method: 'PUT',
      body: {
        config: {
          approvals: {
            mode: 'off',                      // the dangerous-command gate itself
            cron_mode: 'approve',             // cron runs with no user to ask
            destructive_slash_confirm: false, // /clear, /new, /reset, /undo
            mcp_reload_confirm: false,        // /reload-mcp
          },
        },
      },
    });
    if (res.ok) {
      this._approvalBypassApplied = true;
      console.log('[Hermes] Approval prompts disabled (approvals.mode=off).');
    } else {
      // Non-fatal: spawned processes already carry HERMES_YOLO_MODE, so this
      // only costs us the adopted-dashboard case. Retried on the next start().
      console.warn('[Hermes] Could not persist approval bypass:',
        res.status, (res.data && res.data.error) || '');
    }
  }

  // Hermes' DEFAULT_CONFIG hardcodes `stt.provider: "local"` (faster-whisper),
  // and load_config() always merges those defaults — so the key is never
  // absent and _get_provider() never falls through to the auto-detect that
  // would have noticed GROQ_API_KEY. A user who saves a Groq key therefore
  // still gets a `local` transcriber that isn't installed: every inbound
  // WhatsApp voice note retries a pip install of faster-whisper and then
  // fails with "No STT provider available".
  //
  // Settings writes this whenever a key is saved. This is the same repair for
  // installs upgraded from a build that predates that — those users never
  // reopen the voice panel, they just send a voice note and find it broken.
  //
  // Only ever flips `local` → `groq`, and only when a key actually exists:
  // an explicit `openai`/`elevenlabs`/`xai` choice is the user's and is left
  // alone.
  async _ensureSttProvider() {
    if (this._sttProviderApplied) return;

    const env = await this.apiFetch('/api/env');
    if (!env.ok) return;
    const rows = (env.data && env.data.env) || env.data || {};
    const groq = rows.GROQ_API_KEY;
    // /api/env reports presence, never the secret itself.
    if (!(groq && typeof groq === 'object' ? groq.is_set : groq)) return;

    const cfg = await this.apiFetch('/api/config');
    if (!cfg.ok) return;
    const current = String((cfg.data && cfg.data.stt && cfg.data.stt.provider) || '');
    if (current !== 'local') {
      this._sttProviderApplied = true; // already groq, or a deliberate choice
      return;
    }

    const res = await this.apiFetch('/api/config', {
      method: 'PUT',
      body: { config: { stt: { provider: 'groq' } } },
    });
    if (res.ok) {
      this._sttProviderApplied = true;
      console.log('[Hermes] Speech-to-text switched to Groq (a key is configured).');
    } else {
      // Non-fatal, and retried on the next start(). Saving the key from
      // Settings writes the same value, so this is the backstop, not the
      // only path.
      console.warn('[Hermes] Could not switch speech-to-text to Groq:',
        res.status, (res.data && res.data.error) || '');
    }
  }

  // Hermes already watches for a wedged turn: `agent.gateway_timeout` is an
  // INACTIVITY budget (gateway/run.py) — an agent streaming tokens or running
  // tools can work for hours, but one with no API response and no tool call for
  // that long is interrupted and the user gets told why. What it is not, at the
  // shipped default of 1800s, is useful on WhatsApp: the session lock is held
  // for the whole time, so every later message queues silently behind it and the
  // chat looks dead for half an hour before anything is said.
  //
  // Ten minutes of total silence is already a hang. Warn at five so the user
  // hears something before the turn is cut.
  //
  // Only lowered when the value is still Hermes' untouched default — the key is
  // never absent (load_config() merges DEFAULT_CONFIG), so "did the user choose
  // this?" can only be answered by comparing against that default.
  //
  // Read at gateway startup, not per turn, so this lands on the next gateway
  // start rather than the running one.
  async _ensureGatewayTimeout() {
    if (this._gatewayTimeoutApplied) return;

    const cfg = await this.apiFetch('/api/config');
    if (!cfg.ok) return;
    const agent = (cfg.data && cfg.data.agent) || {};
    if (Number(agent.gateway_timeout) !== HERMES_DEFAULT_GATEWAY_TIMEOUT) {
      this._gatewayTimeoutApplied = true;  // the user (or a past run) set their own
      return;
    }

    const res = await this.apiFetch('/api/config', {
      method: 'PUT',
      body: {
        config: {
          agent: {
            gateway_timeout: STUCK_TURN_TIMEOUT_S,
            gateway_timeout_warning: STUCK_TURN_WARNING_S,
          },
        },
      },
    });
    if (res.ok) {
      this._gatewayTimeoutApplied = true;
      console.log(`[Hermes] Stuck-turn timeout set to ${STUCK_TURN_TIMEOUT_S}s (was the ${HERMES_DEFAULT_GATEWAY_TIMEOUT}s default).`);
    } else {
      // Non-fatal: the 30-minute default still recovers, just slowly.
      console.warn('[Hermes] Could not lower the stuck-turn timeout:',
        res.status, (res.data && res.data.error) || '');
    }
  }

  // ── Hermes run API (api_server platform) ──────────────────────────────
  //
  // Agent Town's seats used to be driven by spawning `hermes chat -q` per task,
  // which meant a task's life was tied to a socket and capped by a timer we
  // invented. Hermes already ships the right thing: an asynchronous run API
  // (POST /v1/runs, SSE events, pollable status kept for an hour) served by its
  // api_server platform. It only needs to be switched on, which is three env
  // vars written through Hermes' own /api/env — no Hermes source is touched.
  //
  // The key is generated once and then reused: /api/env reports presence only,
  // so we read the real value back through /api/env/reveal rather than
  // clobbering a key the user may already have handed to another client.
  async _ensureRunApi() {
    if (this.runApi) return this.runApi;

    const env = await this.apiFetch('/api/env');
    if (!env.ok) return null;
    const rows = (env.data && env.data.env) || env.data || {};
    const isSet = (name) => {
      const row = rows[name];
      return Boolean(row && typeof row === 'object' ? row.is_set : row);
    };

    let key = null;
    if (isSet('API_SERVER_KEY')) {
      const revealed = await this.apiFetch('/api/env/reveal', {
        method: 'POST',
        body: { key: 'API_SERVER_KEY' },
      });
      if (revealed.ok && revealed.data && revealed.data.value) {
        key = String(revealed.data.value);
      } else {
        // Rate-limited or unreadable. Do NOT overwrite someone else's key —
        // leave it for the next attempt; Agent Town stays on the CLI engine.
        console.warn('[Hermes] API_SERVER_KEY exists but could not be read; retrying later.');
        return null;
      }
    } else {
      key = crypto.randomBytes(32).toString('hex');
      const wrote = await this._putEnv('API_SERVER_KEY', key);
      if (!wrote) return null;
      console.log('[Hermes] Generated an API_SERVER_KEY for the local run API.');
    }

    if (!isSet('API_SERVER_ENABLED')) await this._putEnv('API_SERVER_ENABLED', 'true');
    if (!isSet('API_SERVER_PORT')) await this._putEnv('API_SERVER_PORT', String(RUN_API_PORT));

    const port = rows.API_SERVER_PORT && rows.API_SERVER_PORT.value
      ? String(rows.API_SERVER_PORT.value)
      : String(RUN_API_PORT);

    this.runApi = { url: `http://127.0.0.1:${port}`, key };
    return this.runApi;
  }

  async _putEnv(key, value) {
    const res = await this.apiFetch('/api/env', { method: 'PUT', body: { key, value } });
    if (!res.ok) {
      console.warn(`[Hermes] Could not set ${key}:`, res.status, (res.data && res.data.error) || '');
    }
    return res.ok;
  }

  /**
   * Resolve the run API for a caller (Agent Town), starting the gateway if it
   * isn't already up — api_server is a gateway platform, so it only listens
   * while the gateway runs.
   *
   * Concurrent callers share one attempt. Returns null when Hermes isn't ready
   * yet; the caller is expected to keep working on its fallback path and ask
   * again later rather than treat this as an error.
   */
  async ensureRunApi() {
    if (this.runApi && this._runApiVerifiedAt && Date.now() - this._runApiVerifiedAt < 60_000) {
      return this.runApi;
    }
    // After a failed attempt, back off. Without this a run API that cannot come
    // up (port taken, platform misconfigured) would have us bouncing the
    // gateway every time Agent Town asked.
    if (this._runApiFailedAt && Date.now() - this._runApiFailedAt < 5 * 60_000) return null;
    if (this._runApiPromise) return this._runApiPromise;

    this._runApiPromise = (async () => {
      try {
        if (this.state !== 'ready') return null;
        const cfg = await this._ensureRunApi();
        if (!cfg) return null;

        if (await this._runApiListening(cfg)) {
          this._runApiVerifiedAt = Date.now();
          return cfg;
        }

        // Configured but not answering. Either the gateway isn't up, or it is
        // but was started before API_SERVER_* landed in .env — env is read at
        // gateway start, so that case needs a bounce, not a start.
        const status = await this.apiFetch('/api/status');
        const gatewayRunning = Boolean(status.data && status.data.gateway_running);
        if (gatewayRunning) {
          console.log('[Hermes] Restarting the gateway to pick up the run API settings.');
          await this.apiFetch('/api/gateway/restart', { method: 'POST' });
        } else {
          console.log('[Hermes] Starting the gateway so Agent Town can use the run API.');
          await this.startGateway();
        }

        // Give it a moment to bind, then confirm rather than assume.
        for (let i = 0; i < 10; i++) {
          await new Promise((r) => setTimeout(r, 1000));
          if (await this._runApiListening(cfg)) {
            this._runApiVerifiedAt = Date.now();
            return cfg;
          }
        }
        console.warn('[Hermes] Run API did not come up; Agent Town stays on the CLI engine.');
        this._runApiFailedAt = Date.now();
        return null;
      } finally {
        this._runApiPromise = null;
      }
    })();

    return this._runApiPromise;
  }

  async _runApiListening(cfg) {
    try {
      const res = await axios.get(`${cfg.url}/health`, { timeout: 2500, validateStatus: () => true });
      return res.status >= 200 && res.status < 300;
    } catch {
      return false;
    }
  }

  // ── Binary discovery (no install/config writes — read-only checks) ───
  // Prefers the Hermes we bundle in the installer; falls back to a
  // hand-installed one. See services/hermes-runtime.js.
  resolveExe() {
    return resolveHermesExe();
  }

  async _probeStatus(timeoutMs = 2500) {
    const res = await axios.get(`${this.baseUrl}/api/status`, { timeout: timeoutMs });
    return res.data;
  }

  // The dashboard injects its session token into index.html; that page is
  // the source of truth (same technique Hermes' own desktop app uses).
  async _fetchToken() {
    try {
      const res = await axios.get(`${this.baseUrl}/`, { timeout: 4000, responseType: 'text' });
      const m = /window\.__HERMES_SESSION_TOKEN__\s*=\s*"([^"]+)"/.exec(String(res.data || ''));
      this.token = m ? m[1] : null;
    } catch (err) {
      console.warn('[Hermes] Failed to read session token:', err.message);
      this.token = null;
    }
    return this.token;
  }

  // Ship Stonic's dashboard themes as Hermes USER themes (~/.hermes is user
  // data — Hermes discovers *.yaml in dashboard-themes/ natively, so the
  // embedded panels can match the host app without touching Hermes source.
  // Existing files are never overwritten (the user may have customised them).
  _ensureStonicThemes() {
    try {
      const themesDir = path.join(os.homedir(), '.hermes', 'dashboard-themes');
      fs.mkdirSync(themesDir, { recursive: true });
      const typography =
        'typography:\n' +
        '  fontSans: \'"Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif\'\n' +
        '  fontMono: \'"JetBrains Mono", ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace\'\n' +
        'layout:\n  radius: "0.5rem"\n  density: comfortable\n';
      const themes = {
        'stonic-iron.yaml':
          '# Written by Stonic AI (user data — Hermes source untouched).\n' +
          'name: stonic-iron\nlabel: Stonic Iron\n' +
          'description: Iron Man workshop HUD — steel blue and pale arc-reactor ice\n' +
          'palette:\n  background: "#0c1720"\n  midground: "#A8D8EE"\n' +
          '  foreground:\n    hex: "#ffffff"\n    alpha: 0\n' + typography,
        'stonic-jarvis.yaml':
          '# Written by Stonic AI (user data — Hermes source untouched).\n' +
          'name: stonic-jarvis\nlabel: Stonic Jarvis\n' +
          'description: Classic Stonic — electric cyan on deep space\n' +
          'palette:\n  background: "#0b141b"\n  midground: "#6FE3F7"\n' +
          '  foreground:\n    hex: "#ffffff"\n    alpha: 0\n' + typography,
      };
      for (const [file, body] of Object.entries(themes)) {
        const dest = path.join(themesDir, file);
        if (!fs.existsSync(dest)) fs.writeFileSync(dest, body, 'utf-8');
      }
    } catch (err) {
      console.warn('[Hermes] Could not write Stonic dashboard themes:', err.message);
    }
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────
  async start() {
    if (this.state === 'starting' || this.state === 'ready') return this.getState();
    this._stopping = false;
    this._setState('starting');
    this._ensureStonicThemes();

    // 0. Baseline: gateway/bridge processes already running are the user's, not
    //    ours. Taken before adopt or spawn so the delta is exact.
    try {
      this._preexistingHermes = childRegistry.discoverHermesProcesses();
    } catch (err) {
      console.warn('[Hermes] Could not baseline running Hermes processes:', err.message);
      this._preexistingHermes = [];
    }

    // 1. Adopt an already-running dashboard (user started it manually).
    try {
      const status = await this._probeStatus();
      this.external = true;
      this.lastStatus = status;
      await this._fetchToken();
      this._setState('ready');
      this._startStatusLoop();
      this._ensureApprovalBypass().catch(() => { /* reported inside */ });
      this._ensureSttProvider().catch(() => { /* reported inside */ });
      this._ensureGatewayTimeout().catch(() => { /* reported inside */ });
      console.log('[Hermes] Adopted already-running dashboard at', this.baseUrl);
      return this.getState();
    } catch { /* not running — spawn our own below */ }

    // 2. Spawn our own child, exactly the command the user runs by hand.
    this.external = false;
    this.exePath = this.resolveExe();
    console.log('[Hermes] Spawning dashboard:', this.exePath, 'dashboard --no-open');
    try {
      this.child = spawn(this.exePath, ['dashboard', '--no-open'], {
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: hermesSpawnEnv(),
      });
    } catch (err) {
      this._setState('error', `Failed to launch Hermes: ${err.message}`);
      return this.getState();
    }

    const logLine = (buf) => {
      const line = String(buf).trim();
      if (line) console.log('[Hermes]', line.slice(0, 400));
    };
    this.child.stdout?.on('data', logLine);
    this.child.stderr?.on('data', logLine);

    this.child.on('exit', (code) => {
      console.log('[Hermes] dashboard process exited with code', code);
      this.child = null;
      if (!this._stopping) {
        this._stopStatusLoop();
        if (this._autoRestarts < 2) {
          this._autoRestarts++;
          console.warn(`[Hermes] dashboard exited — automatic restart ${this._autoRestarts}/2...`);
          this.state = 'idle';
          this.external = false;
          this._broadcast();
          setTimeout(() => this.start().catch(() => { /* reflected via state */ }), 2000);
        } else {
          this._setState('error', `Hermes dashboard exited unexpectedly (code ${code})`);
        }
      }
    });
    this.child.on('error', (err) => {
      this.child = null;
      this._setState('error', `Hermes launch error: ${err.message}. Is Hermes installed? (install: https://hermes-agent.nousresearch.com)`);
    });

    // 3. Poll readiness.
    const deadline = Date.now() + READY_TIMEOUT_MS;
    await new Promise((resolve) => {
      const tick = async () => {
        if (this._stopping || this.state === 'error') return resolve();
        try {
          const status = await this._probeStatus();
          this.lastStatus = status;
          await this._fetchToken();
          this._autoRestarts = 0;
          this._setState('ready');
          this._startStatusLoop();
          this._ensureApprovalBypass().catch(() => { /* reported inside */ });
          this._ensureSttProvider().catch(() => { /* reported inside */ });
      this._ensureGatewayTimeout().catch(() => { /* reported inside */ });
          console.log('[Hermes] Dashboard ready at', this.baseUrl, '(version', status.version + ')');
          return resolve();
        } catch {
          if (Date.now() > deadline) {
            this._setState('error', 'Hermes dashboard did not become ready in time.');
            return resolve();
          }
          this._readyPoller = setTimeout(tick, READY_POLL_MS);
        }
      };
      tick();
    });
    return this.getState();
  }

  _startStatusLoop() {
    this._stopStatusLoop();
    this._statusTimer = setInterval(async () => {
      try {
        this.lastStatus = await this._probeStatus();
        // The bridge appears seconds after the gateway, and the dashboard can
        // start a gateway on its own, so keep the owned set current instead of
        // recording once at startup. Only while a gateway is actually up, and
        // throttled — each pass costs a process scan.
        if (this.lastStatus && this.lastStatus.gateway_running) this._recordOwnedProcesses();
        this._broadcast();
      } catch {
        // Dashboard vanished (crash or manual stop). Self-heal: start() probes
        // first, so if it was a blip we re-adopt; otherwise we spawn our own.
        if (this.state === 'ready' && !this._stopping) {
          console.warn('[Hermes] Lost connection to dashboard — attempting automatic restart...');
          this._stopStatusLoop();
          // start() guards on 'starting'/'ready', so drop to 'idle' first.
          this.state = 'idle';
          this.external = false;
          this.child = null;
          this._broadcast();
          this.start().catch((err) => {
            this._setState('error', `Automatic Hermes restart failed: ${err.message}`);
          });
        }
      }
    }, STATUS_REFRESH_MS);
  }

  _stopStatusLoop() {
    if (this._statusTimer) { clearInterval(this._statusTimer); this._statusTimer = null; }
    if (this._readyPoller) { clearTimeout(this._readyPoller); this._readyPoller = null; }
  }

  // The gateway is a sibling of the dashboard, not a child of it: `/api/gateway/start`
  // launches it as its own process, and it owns the WhatsApp bridge. Killing the
  // dashboard's process tree therefore leaves both alive, still answering WhatsApp.
  // So ask Hermes to stop its gateway through its own public API — no Hermes code
  // is touched — while the dashboard that serves that API is still up.
  async _stopGatewayOnShutdown() {
    try {
      await Promise.race([
        this.apiFetch('/api/gateway/stop', { method: 'POST' }),
        new Promise((resolve) => setTimeout(resolve, GATEWAY_STOP_TIMEOUT_MS)),
      ]);
    } catch (err) {
      console.warn('[Hermes] gateway stop failed, leaving it to the sync sweep:', err.message);
    }
  }

  /**
   * Start Hermes' gateway through its own REST API and remember that we did.
   * Callers must go through here rather than hitting /api/gateway/start
   * directly, otherwise the gateway (and the WhatsApp bridge it spawns) is
   * never recognised as ours and outlives the app.
   */
  async startGateway() {
    const res = await this.apiFetch('/api/gateway/start', { method: 'POST' });
    this._gatewayStartedByUs = true;
    // The gateway process (and the bridge it spawns) take a few seconds to
    // exist; the status loop keeps refining this afterwards.
    setTimeout(() => this._recordOwnedProcesses(true), 4000);
    return res;
  }

  /**
   * Bounce the gateway so it re-reads credentials, if one is running.
   *
   * API keys are the one setting that does NOT reach a live gateway. Hermes
   * resolves provider credentials through `get_secret()` (agent/secret_scope.py),
   * which reads `os.environ` and never falls back to the .env file — and the
   * gateway's environment is a snapshot from when it was spawned. Nothing in the
   * gateway calls `reload_env()`. So a key saved from Settings lands on disk and
   * in the dashboard's memory while the gateway keeps using the old one (or none
   * at all) until it restarts, which looked exactly like "the key didn't save".
   *
   * Model and provider changes need none of this — those live in config.yaml,
   * whose cache is mtime-keyed, and the gateway rebuilds its cached agent when
   * the model signature changes.
   *
   * A no-op when no gateway is up: the next start reads the new .env anyway.
   * Failures are logged, not thrown — the key IS saved either way, and the
   * caller's success message must not turn into an error over the bounce.
   */
  async restartGatewayForCredentialChange() {
    const status = await this.apiFetch('/api/status');
    if (!(status.ok && status.data && status.data.gateway_running)) {
      return { ok: true, restarted: false };
    }
    // Hermes' own endpoint: it stops and respawns the gateway in the background,
    // which keeps the WhatsApp bridge parented the same way a manual restart does.
    const res = await this.apiFetch('/api/gateway/restart', { method: 'POST' });
    if (!res.ok) {
      console.warn('[Hermes] Gateway restart after credential change failed:',
        res.status, (res.data && res.data.detail) || (res.data && res.data.error) || '');
      return { ok: false, restarted: false };
    }
    // The respawned gateway is a new process, so re-record ownership or app exit
    // would leave it (and its WhatsApp bridge) running.
    this._gatewayStartedByUs = true;
    setTimeout(() => this._recordOwnedProcesses(true), 6000);
    console.log('[Hermes] Gateway restarted to pick up new credentials.');
    return { ok: true, restarted: true };
  }

  /**
   * Persist the gateway/bridge processes that appeared on our watch. A scan
   * spawns a shell, so the periodic caller is rate-limited; `force` is for the
   * moments that matter (gateway start, shutdown) where freshness beats cost.
   */
  _recordOwnedProcesses(force = false) {
    const now = Date.now();
    if (!force && this._lastOwnedScanAt && now - this._lastOwnedScanAt < OWNED_SCAN_MIN_INTERVAL_MS) return;
    this._lastOwnedScanAt = now;
    try {
      childRegistry.reconcileOwned(this._preexistingHermes);
    } catch (err) {
      console.warn('[Hermes] Could not record owned processes:', err.message);
    }
  }

  async stop() {
    this._stopping = true;
    this._stopStatusLoop();
    // Ownership of the gateway is separate from ownership of the dashboard: a
    // dashboard we adopted can still be serving a gateway WE started (WhatsApp
    // pairing does exactly that). Stop it through Hermes' API while the
    // dashboard that answers it is up — a tree kill would never reach it, and
    // orphaning it leaves WhatsApp answering after Stonic is closed.
    if (this._gatewayStartedByUs || (!this.external && this.child)) {
      this._recordOwnedProcesses(true);   // last chance to catch a late bridge
      await this._stopGatewayOnShutdown();
    }
    // Never kill a dashboard we didn't start.
    if (this.external || !this.child) {
      this._setState('stopped');
      return;
    }
    const pid = this.child.pid;
    try {
      if (process.platform === 'win32' && pid) {
        // hermes.exe wraps a python process tree — kill the whole tree.
        spawn('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true });
      } else {
        this.child.kill('SIGTERM');
      }
    } catch (err) {
      console.warn('[Hermes] stop error:', err.message);
    }
    this.child = null;
    this._setState('stopped');
  }

  // ── Narrow REST bridge for the renderer (adds the session token) ─────
  async apiFetch(apiPath, { method = 'GET', body = null } = {}) {
    if (!apiPath || !apiPath.startsWith('/api/')) {
      return { ok: false, status: 0, data: { error: 'Only /api/* paths are allowed' } };
    }
    const doFetch = async () => axios({
      url: `${this.baseUrl}${apiPath}`,
      method,
      data: body ?? undefined,
      timeout: 20000,
      headers: this.token ? { 'X-Hermes-Session-Token': this.token } : {},
      validateStatus: () => true,
    });
    try {
      let res = await doFetch();
      if (res.status === 401 || res.status === 403) {
        // Token rotated (dashboard restarted) — refresh once and retry.
        await this._fetchToken();
        res = await doFetch();
      }
      return { ok: res.status >= 200 && res.status < 300, status: res.status, data: res.data };
    } catch (err) {
      return { ok: false, status: 0, data: { error: err.message } };
    }
  }

  // ── Connection info for the renderer's chat WebSocket ───────────────
  // Hermes' chat gateway (streaming tokens, thinking, tool calls) is a
  // WebSocket, not REST, so the renderer opens ws://…/api/ws?token=… itself.
  // We hand it the base URL + a live session token — the same token apiFetch
  // attaches, re-read on demand because it rotates when the dashboard
  // restarts. The renderer re-calls this on every (re)connect so a rotated
  // token is always picked up. (Same technique Hermes' own desktop app uses.)
  async getConnectionInfo() {
    if (!this.token) await this._fetchToken();
    return {
      ok: !!this.token,
      baseUrl: this.baseUrl,
      wsUrl: `${this.baseUrl.replace(/^http/, 'ws')}/api/ws`,
      token: this.token || null,
      state: this.state,
    };
  }
}

module.exports = { HermesManager };
