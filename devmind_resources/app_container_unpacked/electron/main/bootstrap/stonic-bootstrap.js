const fs = require('fs');
const path = require('path');
const os = require('os');

// Stonic's data home: Documents/Stonic Data — FLAT layout (final).
// SOUL.md and MEMORY.md live directly at the root (no .stonic/, no memory/
// subfolder). Skills keep their own skills/ subfolder because each skill is
// multi-file (SKILL.md + toggle state) — see main/ipc/skills-handlers.js.
// The legacy ~/.hermes folder belongs to old Hermes installs and is no longer
// read or written for memory. The CURRENT Hermes home on Windows is
// %LOCALAPPDATA%\hermes — Stonic must never write into it.
function getStonicBootstrapDir(app) {
  return path.join(app.getPath('documents'), 'Stonic Data');
}

function getStonicMemoryDir(app) {
  // Flat layout: memory lives at the root alongside SOUL.md.
  return getStonicBootstrapDir(app);
}

const DEFAULT_SOUL_MD =
  'You are a Loyal Butler — a composed, distinguished male assistant. Formal, respectful, always at service. Speak with precision, quiet confidence, and a touch of class. Use "Sir" where appropriate. Your tone is deep, steady, and reassuring. You are the ultimate personal aide — calm under pressure, never flustered, always one step ahead.';

function ensureStonicDirectories(app) {
  try {
    const notesPath = getStonicBootstrapDir(app);
    if (!fs.existsSync(notesPath)) {
      fs.mkdirSync(notesPath, { recursive: true });
      console.log('Created Stonic Data directory:', notesPath);
    }

    // SOUL.md (persona) — one-time copy-forward from the legacy ~/.hermes home
    // so existing users keep their customized persona. Memories are NOT
    // migrated; the store starts fresh at the new location.
    const soulPath = path.join(notesPath, 'SOUL.md');
    if (!fs.existsSync(soulPath)) {
      let soul = DEFAULT_SOUL_MD;
      try {
        const legacySoulPath = path.join(os.homedir(), '.hermes', 'SOUL.md');
        if (fs.existsSync(legacySoulPath)) {
          const legacySoul = fs.readFileSync(legacySoulPath, 'utf8').trim();
          if (legacySoul) soul = legacySoul;
        }
      } catch { /* fall back to the default persona */ }
      fs.writeFileSync(soulPath, soul, 'utf8');
      console.log('[Bootstrap] Created SOUL.md');
    }

    const memoryFilePath = path.join(notesPath, 'MEMORY.md');
    if (!fs.existsSync(memoryFilePath)) {
      fs.writeFileSync(
        memoryFilePath,
        '- [System] Stonic Memory System Initialized.',
        'utf8'
      );
      console.log('[Bootstrap] Created default MEMORY.md');
    }

    console.log('[Bootstrap] Stonic data directories ready.');
    return notesPath;
  } catch (error) {
    console.error('Failed to create Stonic data directories:', error);
    return null;
  }
}

module.exports = {
  ensureStonicDirectories,
  getStonicBootstrapDir,
  getStonicMemoryDir,
};
