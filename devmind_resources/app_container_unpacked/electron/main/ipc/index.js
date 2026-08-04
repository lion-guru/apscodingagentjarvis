const { registerSkillsHandlers } = require('./skills-handlers');
const { registerSystemHandlers } = require('./system-handlers');
const { registerHardwareHandlers } = require('./hardware-handlers');
const { registerWhatsAppHandlers } = require('./whatsapp-handlers');
const { registerHermesHandlers } = require('./hermes-handlers');
const { registerAgentTownHandlers } = require('./agenttown-handlers');

// Shared state for cross-module access (set by main.js after window creation)
let _mainWindow = null;
let _hermesManager = null;
let _agentTownManager = null;

function registerDomainHandlers() {
  registerSystemHandlers();
  registerSkillsHandlers();
  registerHardwareHandlers();
  registerWhatsAppHandlers();
  registerHermesHandlers({
    getHermesManager: () => _hermesManager,
  });
  registerAgentTownHandlers({
    getAgentTownManager: () => _agentTownManager,
  });
}

function setMainWindow(win) { _mainWindow = win; }
function getMainWindow() { return _mainWindow; }
function getHermesManager() { return _hermesManager; }
function setHermesManager(mgr) { _hermesManager = mgr; }
function getAgentTownManager() { return _agentTownManager; }
function setAgentTownManager(mgr) { _agentTownManager = mgr; }

module.exports = {
  registerDomainHandlers,
  setMainWindow,
  getMainWindow,
  getHermesManager,
  setHermesManager,
  getAgentTownManager,
  setAgentTownManager,
};
