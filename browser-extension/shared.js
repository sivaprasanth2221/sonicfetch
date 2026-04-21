const DEFAULT_SETTINGS = {
  backendUrl: "http://127.0.0.1:8000",
  dashboardUrl: "http://localhost:5173",
  audioFormat: "mp3",
  audioQuality: "192",
  openDashboard: true
};

const YOUTUBE_HOSTS = new Set([
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "music.youtube.com",
  "youtu.be",
  "www.youtu.be"
]);

function getExtensionApi() {
  if (globalThis.browser) {
    return globalThis.browser;
  }
  if (globalThis.chrome) {
    return globalThis.chrome;
  }
  throw new Error("Browser extension APIs are unavailable.");
}

function normalizeBackendUrl(value) {
  return (value || DEFAULT_SETTINGS.backendUrl).trim().replace(/\/+$/, "");
}

function normalizeDashboardUrl(value) {
  return (value || DEFAULT_SETTINGS.dashboardUrl).trim().replace(/\/+$/, "");
}

function storageGet(keys) {
  const api = getExtensionApi();
  return new Promise((resolve, reject) => {
    const callback = (result) => {
      const runtimeError = globalThis.chrome?.runtime?.lastError;
      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }
      resolve(result);
    };

    const request = api.storage.local.get(keys, callback);
    if (request && typeof request.then === "function") {
      request.then(resolve).catch(reject);
    }
  });
}

function storageSet(values) {
  const api = getExtensionApi();
  return new Promise((resolve, reject) => {
    const callback = () => {
      const runtimeError = globalThis.chrome?.runtime?.lastError;
      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }
      resolve();
    };

    const request = api.storage.local.set(values, callback);
    if (request && typeof request.then === "function") {
      request.then(resolve).catch(reject);
    }
  });
}

async function getSettings() {
  const stored = await storageGet(Object.keys(DEFAULT_SETTINGS));
  return {
    ...DEFAULT_SETTINGS,
    ...stored,
    backendUrl: normalizeBackendUrl(stored.backendUrl || DEFAULT_SETTINGS.backendUrl),
    dashboardUrl: normalizeDashboardUrl(stored.dashboardUrl || DEFAULT_SETTINGS.dashboardUrl)
  };
}

function isYouTubeUrl(value) {
  try {
    const parsed = new URL(value);
    return YOUTUBE_HOSTS.has(parsed.hostname.toLowerCase());
  } catch {
    return false;
  }
}

async function sendToSonicFetch(url, overrides = {}) {
  const settings = {
    ...(await getSettings()),
    ...overrides
  };
  const backendUrl = normalizeBackendUrl(settings.backendUrl);

  const response = await fetch(`${backendUrl}/api/downloads`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      url,
      audioFormat: settings.audioFormat,
      audioQuality: settings.audioQuality
    })
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Unable to send the URL to SonicFetch.");
  }

  if (settings.openDashboard) {
    await openDashboard(settings.dashboardUrl);
  }

  return payload;
}

async function openDashboard(dashboardUrl) {
  const api = getExtensionApi();
  const url = normalizeDashboardUrl(dashboardUrl);
  if (api.tabs?.create) {
    await api.tabs.create({ url });
  }
}

async function getCurrentTabUrl() {
  const api = getExtensionApi();
  const tabs = await api.tabs.query({ active: true, currentWindow: true });
  return tabs[0]?.url || "";
}

async function notify(title, message) {
  const api = getExtensionApi();
  if (!api.notifications?.create) {
    return;
  }

  await api.notifications.create({
    type: "basic",
    iconUrl: "assets/icon-128.png",
    title,
    message
  });
}

export {
  DEFAULT_SETTINGS,
  getCurrentTabUrl,
  getExtensionApi,
  getSettings,
  isYouTubeUrl,
  notify,
  openDashboard,
  sendToSonicFetch,
  storageSet
};
