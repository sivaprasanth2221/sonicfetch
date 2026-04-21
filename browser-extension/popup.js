import {
  getCurrentTabUrl,
  getExtensionApi,
  getSettings,
  isYouTubeUrl,
  openDashboard,
  sendToSonicFetch,
  storageSet
} from "./shared.js";

const api = getExtensionApi();

const form = document.querySelector("#send-form");
const urlInput = document.querySelector("#url");
const formatSelect = document.querySelector("#audioFormat");
const qualitySelect = document.querySelector("#audioQuality");
const statusEl = document.querySelector("#status");
const backendUrlInput = document.querySelector("#backendUrl");
const dashboardUrlInput = document.querySelector("#dashboardUrl");
const openDashboardCheckbox = document.querySelector("#openDashboard");
const popupSettingsForm = document.querySelector("#popup-settings-form");
const settingsStatusEl = document.querySelector("#settings-status");
const toggleSettingsButton = document.querySelector("#toggle-settings");
const useCurrentTabButton = document.querySelector("#use-current-tab");
const openDashboardButton = document.querySelector("#open-dashboard");
const openOptionsButton = document.querySelector("#open-options");

function setStatus(element, message, type = "") {
  element.textContent = message;
  element.className = `status${type ? ` status-${type}` : ""}`;
}

function setSendStatus(message, type = "") {
  setStatus(statusEl, message, type);
}

function setSettingsStatus(message, type = "") {
  setStatus(settingsStatusEl, message, type);
}

function setSettingsVisibility(isVisible) {
  popupSettingsForm.classList.toggle("hidden", !isVisible);
  toggleSettingsButton.textContent = isVisible ? "Hide" : "Show";
}

async function populateFromSettings() {
  const settings = await getSettings();
  formatSelect.value = settings.audioFormat;
  qualitySelect.value = settings.audioQuality;
  backendUrlInput.value = settings.backendUrl;
  dashboardUrlInput.value = settings.dashboardUrl;
  openDashboardCheckbox.checked = Boolean(settings.openDashboard);

  const currentTabUrl = await getCurrentTabUrl();
  if (isYouTubeUrl(currentTabUrl)) {
    urlInput.value = currentTabUrl;
    setSendStatus("Current YouTube tab detected.", "success");
  }
}

useCurrentTabButton.addEventListener("click", async () => {
  const currentTabUrl = await getCurrentTabUrl();
  if (!isYouTubeUrl(currentTabUrl)) {
    setSendStatus("Open a YouTube video or playlist tab first.", "error");
    return;
  }
  urlInput.value = currentTabUrl;
  setSendStatus("Current tab URL loaded.", "success");
});

openDashboardButton.addEventListener("click", async () => {
  const settings = await getSettings();
  await openDashboard(settings.dashboardUrl);
});

openOptionsButton.addEventListener("click", () => {
  api.runtime.openOptionsPage();
});

toggleSettingsButton.addEventListener("click", () => {
  const isHidden = popupSettingsForm.classList.contains("hidden");
  setSettingsVisibility(isHidden);
});

popupSettingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await storageSet({
      backendUrl: backendUrlInput.value.trim(),
      dashboardUrl: dashboardUrlInput.value.trim(),
      audioFormat: formatSelect.value,
      audioQuality: qualitySelect.value,
      openDashboard: openDashboardCheckbox.checked
    });
    setSettingsStatus("Settings saved.", "success");
    setSendStatus("Quick settings updated.", "success");
  } catch (error) {
    setSettingsStatus(error.message || "Unable to save settings.", "error");
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = urlInput.value.trim();
  if (!isYouTubeUrl(url)) {
    setSendStatus("Enter a valid YouTube video or playlist URL.", "error");
    return;
  }

  const settings = {
    ...(await getSettings()),
    audioFormat: formatSelect.value,
    audioQuality: qualitySelect.value
  };

  try {
    await storageSet({
      audioFormat: settings.audioFormat,
      audioQuality: settings.audioQuality
    });
    await sendToSonicFetch(url, settings);
    setSendStatus("Sent to SonicFetch successfully.", "success");
  } catch (error) {
    setSendStatus(error.message || "Failed to reach SonicFetch.", "error");
  }
});

populateFromSettings().catch((error) => {
  setSendStatus(error.message || "Failed to load extension settings.", "error");
});
