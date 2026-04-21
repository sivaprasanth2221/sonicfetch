import {
  getExtensionApi,
  isYouTubeUrl,
  notify,
  sendToSonicFetch
} from "./shared.js";

const api = getExtensionApi();

function createMenus() {
  api.contextMenus.removeAll(() => {
    api.contextMenus.create({
      id: "send-current-page",
      title: "Send page to SonicFetch",
      contexts: ["page"]
    });
    api.contextMenus.create({
      id: "send-link",
      title: "Send link to SonicFetch",
      contexts: ["link"]
    });
  });
}

api.runtime.onInstalled.addListener(() => {
  createMenus();
});

api.runtime.onStartup?.addListener(() => {
  createMenus();
});

api.contextMenus.onClicked.addListener(async (info, tab) => {
  const candidateUrl = info.menuItemId === "send-link" ? info.linkUrl : tab?.url || info.pageUrl;
  if (!candidateUrl || !isYouTubeUrl(candidateUrl)) {
    await notify("SonicFetch", "This action only works with YouTube pages or links.");
    return;
  }

  try {
    await sendToSonicFetch(candidateUrl);
    await notify("SonicFetch", "The link was sent to SonicFetch successfully.");
  } catch (error) {
    await notify("SonicFetch", error.message || "Failed to contact SonicFetch.");
  }
});
