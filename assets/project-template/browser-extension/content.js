(() => {
  if (globalThis.__autumnJDClipperInstalled) return;
  globalThis.__autumnJDClipperInstalled = true;

  const limit = (value, size = 800000) => String(value || "").slice(0, size);
  const findJobPostings = () => {
    const results = [];
    const visit = value => {
      if (Array.isArray(value)) return value.forEach(visit);
      if (!value || typeof value !== "object") return;
      const types = Array.isArray(value["@type"]) ? value["@type"] : [value["@type"]];
      if (types.some(type => String(type).toLowerCase() === "jobposting")) results.push(value);
      Object.values(value).forEach(visit);
    };
    document.querySelectorAll('script[type="application/ld+json"]').forEach(node => {
      try { visit(JSON.parse(node.textContent)); } catch (_) { /* invalid page JSON-LD */ }
    });
    return results;
  };
  const candidateFragment = () => {
    const selectors = [
      "[itemprop='description']", ".job-description", ".job-detail", ".job-content",
      ".position-detail", ".position-description", ".job-requirements",
      ".job-responsibilities", "[class*='jobDescription']", "[class*='job-detail']",
      "[class*='position-detail']", "main article", "main"
    ];
    const nodes = selectors.flatMap(selector => Array.from(document.querySelectorAll(selector)));
    nodes.sort((a, b) => (b.innerText || "").length - (a.innerText || "").length);
    return nodes[0] ? limit(nodes[0].outerHTML, 500000) : "";
  };
  const meta = key => document.querySelector(`meta[name="${key}"]`)?.content || "";
  const property = key => document.querySelector(`meta[property="${key}"]`)?.content || "";

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "CAPTURE_JD") return;
    try {
      sendResponse({ok: true, payload: {
        capture_source: "browser_extension",
        url: location.href,
        page_title: document.title,
        selected_text: limit(getSelection()?.toString(), 300000),
        page_text: limit(document.body?.innerText),
        html_fragment: candidateFragment(),
        meta_description: meta("description"),
        og_title: property("og:title"),
        og_description: property("og:description"),
        structured_data: findJobPostings(),
        captured_at: new Date().toISOString(),
        browser_info: navigator.userAgent
      }});
    } catch (error) {
      sendResponse({ok: false, error: error?.message || "capture_failed"});
    }
    return true;
  });
})();
