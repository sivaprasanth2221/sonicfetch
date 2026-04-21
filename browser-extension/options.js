import { getSettings, storageSet } from "./shared.js";

const backendUrlInput = document.querySelector("#backendUrl");
const dashboardUrlInput = document.querySelector("#dashboardUrl");
const formatSelect = document.querySelector("#audioFormat");
const qualitySelect = document.querySelector("#audioQuality");
const openDashboardCheckbox = document.querySelector("#openDashboard");
const form = document.querySelector("#settings-form");
const statusEl = document.querySelector("#status");

function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = `status${type ? ` status-${type}` : ""}`;
}

async function loadSettings() {
  const settings = await getSettings();
  backendUrlInput.value = settings.backendUrl;
  dashboardUrlInput.value = settings.dashboardUrl;
  formatSelect.value = settings.audioFormat;
  qualitySelect.value = settings.audioQuality;
  openDashboardCheckbox.checked = Boolean(settings.openDashboard);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await storageSet({
      backendUrl: backendUrlInput.value.trim(),
      dashboardUrl: dashboardUrlInput.value.trim(),
      audioFormat: formatSelect.value,
      audioQuality: qualitySelect.value,
      openDashboard: openDashboardCheckbox.checked
    });
    setStatus("Settings saved.", "success");
  } catch (error) {
    setStatus(error.message || "Unable to save settings.", "error");
  }
});

loadSettings().catch((error) => {
  setStatus(error.message || "Unable to load settings.", "error");
});
