const $ = id => document.getElementById(id);
let activeTab = null;
let pendingPayload = null;

function setStatus(text) { $("statusText").textContent = text; }
function setBusy(busy) { $("saveButton").disabled = busy; $("rawButton").disabled = busy; }
function shortUrl(value) {
  try { const url = new URL(value); return `${url.hostname}${url.pathname}`.slice(0, 72); }
  catch (_) { return String(value || "").slice(0, 72); }
}

async function currentTab() {
  const tabs = await chrome.tabs.query({active: true, currentWindow: true});
  activeTab = tabs[0] || null;
  $("pageTitle").textContent = activeTab?.title || "无法读取当前页面";
  $("pageUrl").textContent = shortUrl(activeTab?.url);
  $("sourceValue").textContent = activeTab?.url || "无法读取";
}

async function checkHealth() {
  try {
    const data = await ClipperAPI.health();
    if (data.status !== "ok") throw new Error("offline");
    $("offlineCard").hidden = true;
    $("connectionDot").classList.add("online");
    $("saveButton").disabled = false;
    $("savePathValue").textContent = data.save_directory || "本地 JD 库";
    setStatus("已连接本地求职工作台");
    return true;
  } catch (_) {
    $("offlineCard").hidden = false;
    $("connectionDot").classList.remove("online");
    $("saveButton").disabled = true;
    setStatus("");
    return false;
  }
}

async function capture() {
  if (!activeTab?.id) throw new Error("no_tab");
  await chrome.scripting.executeScript({target: {tabId: activeTab.id}, files: ["content.js"]});
  const response = await chrome.tabs.sendMessage(activeTab.id, {type: "CAPTURE_JD"});
  if (!response?.ok) throw new Error("capture_failed");
  return response.payload;
}

function isWeak(payload) {
  const selected = (payload.selected_text || "").length;
  const body = (payload.page_text || "").length;
  const fragment = (payload.html_fragment || "").length;
  const structured = Array.isArray(payload.structured_data) ? payload.structured_data.length : 0;
  return !structured && selected < 80 && fragment < 120 && body < 180;
}

async function submit(payload, raw = false) {
  setBusy(true);
  $("fallbackCard").hidden = true;
  setStatus("正在解析 JD…");
  if (raw) payload = {...payload, selected_text: "", html_fragment: "", structured_data: {}};
  await new Promise(resolve => setTimeout(resolve, 180));
  setStatus("正在保存…");
  const result = await ClipperAPI.save(payload);
  $("resultCard").hidden = false;
  $("resultTitle").textContent = result.status === "already_saved" ? "该岗位已经保存" : "JD 已保存";
  $("resultCompany").textContent = result.company || "公司未识别";
  $("resultPosition").textContent = result.position || "岗位未识别";
  $("resultFile").textContent = result.filename || "";
  $("saveButton").textContent = "再次检查";
  setStatus(result.status === "version_saved" ? "检测到内容更新，已安全保存新版本" : "保存完成");
  setBusy(false);
}

async function save() {
  try {
    setBusy(true);
    $("resultCard").hidden = true;
    setStatus("正在读取页面…");
    pendingPayload = await capture();
    pendingPayload.description = $("descriptionInput").value.trim();
    if (isWeak(pendingPayload)) {
      $("fallbackCard").hidden = false;
      setStatus("建议选中 JD 正文后重试");
      setBusy(false);
      return;
    }
    await submit(pendingPayload);
  } catch (_) {
    setBusy(false);
    setStatus("未能读取此页面，请打开普通招聘网页后重试");
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  $("createdValue").textContent = new Intl.DateTimeFormat("zh-CN", {year: "numeric", month: "2-digit", day: "2-digit"}).format(new Date());
  await currentTab();
  await checkHealth();
  $("saveButton").addEventListener("click", save);
  $("retryButton").addEventListener("click", checkHealth);
  $("rawButton").addEventListener("click", () => pendingPayload && submit(pendingPayload, true));
  $("openButton").addEventListener("click", () => chrome.tabs.create({url: ClipperAPI.base}));
});
