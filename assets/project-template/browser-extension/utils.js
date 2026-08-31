const ClipperAPI = {
  base: "http://127.0.0.1:8765",
  async health() {
    const response = await fetch(`${this.base}/api/health`, {cache: "no-store"});
    if (!response.ok) throw new Error("offline");
    return response.json();
  },
  async save(payload) {
    const response = await fetch(`${this.base}/api/jd/clip`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error("save_failed");
    return response.json();
  }
};
