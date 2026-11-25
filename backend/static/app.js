/* ---------- OpenClipboard — frontend logic ---------- */
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  // ---------------- state ----------------
  const state = {
    kind: "text",            // text | image | file
    file: null,              // selected File (image/file)
    text: "",
    ttl: 900,
    oneShot: false,
  };

  const els = {
    tabs: $$("#kind-tabs .tab"),
    panes: $$(".pane"),
    textInput: $("#text-input"),
    pasteBtn: $("#paste-clipboard"),
    imageInput: $("#image-input"),
    fileInput: $("#file-input"),
    dropzones: $$(".dropzone"),
    previews: $$(".preview"),
    ttlSelect: $("#ttl-select"),
    oneShot: $("#one-shot"),
    sendBtn: $("#send-btn"),
    sendResult: $("#send-result"),
    sendCode: $("#send-code"),
    sendMeta: $("#send-meta"),
    sendCountdown: $("#send-countdown"),
    copyLink: $("#copy-link"),
    retrieveInput: $("#retrieve-code"),
    retrieveBtn: $("#retrieve-btn"),
    retrieveResult: $("#retrieve-result"),
    retrieveContent: $("#retrieve-content"),
    retrieveActions: $("#retrieve-actions"),
    retrieveError: $("#retrieve-error"),
    retrieveName: $("#retrieve-name"),
    retrieveCountdown: $("#retrieve-countdown"),
    retrieveKind: $("#retrieve-kind"),
  };

  // ---------------- tabs ----------------
  els.tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      state.kind = tab.dataset.kind;
      els.tabs.forEach((t) => t.classList.toggle("is-active", t === tab));
      els.panes.forEach((p) => p.classList.toggle("is-active", p.dataset.kind === state.kind));
      resetSendResult();
    });
  });

  // ---------------- text ----------------
  els.textInput.addEventListener("input", (e) => {
    state.text = e.target.value;
    resetSendResult();
  });

  // ---------------- files via click / dropzone ----------------
  const attachDropzone = (dz, input) => {
    dz.addEventListener("click", () => input.click());
    dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("is-drag"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("is-drag"));
    dz.addEventListener("drop", (e) => {
      e.preventDefault(); dz.classList.remove("is-drag");
      const files = e.dataTransfer.files;
      if (files.length) handleFilePick(files[0], input.dataset.kind);
    });
    input.addEventListener("change", (e) => {
      const f = e.target.files[0];
      if (f) handleFilePick(f, input.dataset.kind);
    });
  };

  attachDropzone($(".dropzone[data-drop='image']"), els.imageInput);
  attachDropzone($(".dropzone[data-drop='file']"), els.fileInput);

  function handleFilePick(file, kind) {
    if (kind === "image" && !file.type.startsWith("image/")) {
      alert("Please pick an image file.");
      return;
    }
    state.file = file;
    const preview = $(`.preview[data-preview]`); // only one visible pane matters
    if (kind === "image") {
      const url = URL.createObjectURL(file);
      preview.innerHTML = `<img src="${url}" alt="preview">`;
      preview.hidden = false;
    } else {
      preview.innerHTML = `<span class="dropzone__icon">📦</span><div><strong>${escapeHtml(file.name)}</strong><div class="paste-hint">${formatBytes(file.size)}</div></div>`;
      preview.hidden = false;
    }
    resetSendResult();
  }

  // paste image/text into the active pane (works best on desktop Chrome/Edge)
  window.addEventListener("paste", async (e) => {
    if (document.activeElement === els.textInput) return; // let textarea handle its own paste
    const items = e.clipboardData?.items || [];
    for (const item of items) {
      if (state.kind === "image" && item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) handleFilePick(file, "image");
        return;
      }
      if (state.kind === "text" && item.type === "text/plain") {
        e.preventDefault();
        item.getAsString((text) => {
          els.textInput.value = text;
          state.text = text;
        });
        return;
      }
    }
  });

  // ---------------- options ----------------
  els.ttlSelect.addEventListener("change", (e) => {
    state.ttl = Number(e.target.value);
    resetSendResult();
  });
  els.oneShot.addEventListener("change", (e) => {
    state.oneShot = e.target.checked;
    resetSendResult();
  });

  // ---------------- send ----------------
  els.sendBtn.addEventListener("click", async () => {
    els.sendBtn.disabled = true;
    els.sendBtn.querySelector(".spinner").hidden = false;
    try {
      const form = new FormData();
      form.append("kind", state.kind);
      form.append("ttl", String(state.ttl));
      form.append("one_shot", state.oneShot ? "1" : "0");

      if (state.kind === "text") {
        if (!state.text.trim()) throw new Error("Please type some text first.");
        form.append("text", state.text);
      } else if (state.file) {
        form.append("file", state.file);
      } else {
        throw new Error("Please select a file first.");
      }

      const res = await fetch("/api/send", { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed (${res.status})`);
      }
      const data = await res.json();

      showSendResult(data);
      // focus the retrieve input prefilled with the code on desktop
      els.retrieveInput.value = data.code;
    } catch (err) {
      alert(err.message);
    } finally {
      els.sendBtn.disabled = false;
      els.sendBtn.querySelector(".spinner").hidden = true;
    }
  });

  function showSendResult(data) {
    els.sendResult.hidden = false;
    els.sendCode.textContent = data.code;
    const mins = Math.floor(data.ttl / 60);
    const unit = mins >= 60 ? Math.floor(mins / 60) + " hour" : mins + " minute" + (mins === 1 ? "" : "s");
    els.sendMeta.textContent = `${data.kind.toUpperCase()} • ${formatBytes(data.size)} • ${unit}`;
    startCountdown(els.sendCountdown, new Date(data.expires_at));
    if (data.one_shot) {
      els.sendMeta.textContent += " • one-shot (deleted after first download)";
    }
  }

  function resetSendResult() {
    els.sendResult.hidden = true;
    if (els.sendCountdown) clearInterval(els.sendCountdown.dataset.timer);
  }

  // ---------------- retrieve ----------------
  let retrieveTimer = null;
  els.retrieveInput.addEventListener("input", (e) => {
    // Codes are 12 chars, case-sensitive alphanumeric. Strip anything else.
    e.target.value = e.target.value.replace(/[^A-Za-z0-9]/g, "").slice(0, 12);
    els.retrieveResult.hidden = true;
    els.retrieveError.hidden = true;
    if (retrieveTimer) clearInterval(retrieveTimer);
  });

  els.retrieveBtn.addEventListener("click", () => {
    const code = els.retrieveInput.value.trim();
    if (!/^[A-Za-z0-9]{12}$/.test(code)) {
      showRetrieveError("Please enter the full 12-character code.");
      return;
    }
    fetchCode(code);
  });
  els.retrieveInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") els.retrieveBtn.click();
  });

  async function fetchCode(code) {
    els.retrieveBtn.disabled = true;
    try {
      const res = await fetch(`/api/retrieve/${encodeURIComponent(code)}`);
      if (res.status === 410) {
        showRetrieveError("This code has expired and its content was deleted.");
        return;
      }
      if (res.status === 404) {
        showRetrieveError("No such code. Check the digits or ask the sender to resend.");
        return;
      }
      if (!res.ok) throw new Error(`Lookup failed (${res.status})`);
      const data = await res.json();

      els.retrieveResult.hidden = false;
      els.retrieveError.hidden = true;
      els.retrieveKind.textContent = data.item.kind.toUpperCase();
      els.retrieveKind.className = "kind-badge";

      if (data.item.kind === "text") {
        els.retrieveContent.innerHTML = `<pre>${escapeHtml(data.text ?? "")}</pre>`;
        els.retrieveName.textContent = "Text snippet";
        buildTextActions(data);
      } else {
        const fileUrl = `/api/file/${encodeURIComponent(code)}`;
        if (data.item.kind === "image") {
          els.retrieveContent.innerHTML = `<img src="${fileUrl}" alt="${escapeHtml(data.item.filename)}" loading="lazy">`;
        } else {
          els.retrieveContent.innerHTML = `
            <div style="display:flex;align-items:center;gap:1rem;">
              <span class="dropzone__icon">📦</span>
              <div><div style="font-weight:600">${escapeHtml(data.item.filename || "file")}</div>
              <div class="paste-hint">${formatBytes(data.item.size)}</div></div>
            </div>`;
        }
        els.retrieveName.textContent = data.item.filename || "Attachment";
        buildFileActions(fileUrl, data.item);
      }
      startCountdown(els.retrieveCountdown, new Date(data.item.expires_at));
    } catch (err) {
      showRetrieveError(err.message || "Something went wrong.");
    } finally {
      els.retrieveBtn.disabled = false;
    }
  }

  function showRetrieveError(msg) {
    els.retrieveError.textContent = msg;
    els.retrieveError.hidden = false;
    els.retrieveResult.hidden = true;
  }

  function buildTextActions(data) {
    els.retrieveActions.innerHTML = `
      <button class="btn btn--primary" id="copy-text" type="button">📋 Copy text</button>
      <button class="btn btn--ghost" id="delete-text" type="button">🗑️ Delete now</button>
    `;
    $("#copy-text").addEventListener("click", async () => {
      await navigator.clipboard.writeText(data.text ?? "");
      const btn = $("#copy-text");
      const old = btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(() => btn.textContent = old, 1200);
    });
    $("#delete-text").addEventListener("click", async () => {
      if (!confirm("Delete this clipboard entry now?")) return;
      await fetch(`/api/item/${encodeURIComponent(data.item.code)}`, { method: "DELETE" });
      els.retrieveResult.hidden = true;
      showRetrieveError("Deleted.");
    });
  }

  function buildFileActions(fileUrl, item) {
    els.retrieveActions.innerHTML = `
      <a href="${fileUrl}" download="${item.filename || item.code}" class="btn btn--primary">⬇️ Download</a>
      ${item.one_shot ? "" : `<button class="btn btn--ghost" id="delete-file" type="button">🗑️ Delete now</button>`}
    `;
    const del = $("#delete-file");
    if (del) {
      del.addEventListener("click", async () => {
        if (!confirm("Delete this clipboard entry now?")) return;
        await fetch(`/api/item/${encodeURIComponent(item.code)}`, { method: "DELETE" });
        els.retrieveResult.hidden = true;
        showRetrieveError("Deleted.");
      });
    }
  }

  // ---------------- countdown ----------------
  function startCountdown(el, expiry) {
    if (el.dataset.timer) clearInterval(el.dataset.timer);
    const tick = () => {
      const sec = Math.max(0, Math.floor((expiry - Date.now()) / 1000));
      if (sec === 0) {
        el.textContent = "Expired — content deleted";
        el.style.color = "var(--err)";
        clearInterval(el.dataset.timer);
        return;
      }
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      el.textContent = `Expires in ${m}:${String(s).padStart(2, "0")}`;
    };
    tick();
    el.dataset.timer = setInterval(tick, 1000);
  }

  // ---------------- stats ----------------
  async function refreshStats() {
    try {
      const res = await fetch("/api/stats");
      if (res.ok) {
        const data = await res.json();
        const stats = $("#stats");
        stats.hidden = false;
        $("#stats-active").textContent = data.active;
        $("#stats-bytes").textContent = `• ${formatBytes(data.bytes)}`;
      }
    } catch { /* ignore */ }
  }
  setInterval(refreshStats, 15000);
  refreshStats();

  // ---------------- utils ----------------
  function formatBytes(bytes) {
    if (!bytes && bytes !== 0) return "—";
    if (bytes < 1024) return bytes + " B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Number((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }
  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  // copy share link — copy only the code, not a URL with ?code=
  // (avoids leaking the code in browser history, server logs, Referer headers)
  els.copyLink.addEventListener("click", () => {
    const code = els.sendCode.textContent.trim();
    navigator.clipboard.writeText(code).then(() => {
      const old = els.copyLink.textContent;
      els.copyLink.textContent = "Code copied!";
      setTimeout(() => els.copyLink.textContent = old, 1200);
    });
  });

  // prefill code from ?code= querystring (optional; avoid sharing URLs with codes)
  const params = new URLSearchParams(location.search);
  const prefill = (params.get("code") || "").replace(/[^A-Za-z0-9]/g, "").slice(0, 12);
  if (prefill.length === 12) {
    els.retrieveInput.value = prefill;
    els.retrieveBtn.click();
  }
})();
