(function () {
  const body = document.body || document.documentElement;
  const form = document.querySelector("form.upload-form");
  if (!body || !form) return;

  const fileInput = form.querySelector('input[type="file"][name="file"]');
  if (!fileInput) return;

  const queuePanel = document.getElementById("upload-queue-panel");
  const queueStatus = document.getElementById("upload-queue-status");
  const retryButton = document.getElementById("upload-queue-retry");

  const uploadApiUrl = String(body.getAttribute("data-upload-api-url") || "").trim();
  const csrfApiUrl = String(body.getAttribute("data-upload-csrf-url") || "/api/v1/student/csrf").trim();
  const syncIntervalMs = Number.parseInt(body.getAttribute("data-upload-sync-interval-ms") || "90000", 10);

  const DB_NAME = "classhub_upload_queue_v1";
  const DB_STORE = "uploads";
  const SW_URL = "/student-upload-sync-sw.js";
  const SW_SYNC_TAG = "classhub-upload-queue";

  let cachedCsrfToken = "";
  let isFlushingQueue = false;

  const readI18n = (key, fallback) => {
    const value = String(body.getAttribute(`data-i18n-${key}`) || "").trim();
    return value || fallback;
  };
  const i18n = {
    queued: readI18n("queue-queued", "Upload queued. It will sync when connection returns."),
    syncing: readI18n("queue-syncing", "Syncing queued uploads..."),
    synced: readI18n("queue-synced", "Queued upload synced."),
    syncError: readI18n("queue-sync-error", "Queued upload still waiting for server connection."),
    queueNone: readI18n("queue-none", "No queued uploads."),
    uploadSaved: readI18n("upload-saved", "Upload saved."),
    uploadFailed: readI18n("upload-failed", "Upload failed. Try again when connected."),
    queuePendingCount: readI18n("queue-pending-count", "Queued uploads pending: __COUNT__."),
  };

  const queueSupported = Boolean(window.indexedDB && window.fetch && window.FormData && uploadApiUrl);

  const renderPendingCount = (count) => i18n.queuePendingCount.replace("__COUNT__", String(count));

  const updateQueueStatus = (message, { count = null } = {}) => {
    if (!queuePanel || !queueStatus) return;
    const finalMessage = message || (count && count > 0 ? renderPendingCount(count) : i18n.queueNone);
    queueStatus.textContent = finalMessage;
    const hasQueuedUploads = Number(count || 0) > 0;
    queuePanel.classList.toggle("queue-panel--active", hasQueuedUploads);
    if (retryButton) {
      retryButton.hidden = !hasQueuedUploads;
      retryButton.disabled = !hasQueuedUploads;
    }
  };

  const setRetryEnabled = (enabled) => {
    if (!retryButton) return;
    retryButton.disabled = !enabled;
  };

  const openQueueDb = () => new Promise((resolve, reject) => {
    if (!window.indexedDB) {
      reject(new Error("indexeddb_unavailable"));
      return;
    }
    const request = window.indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(DB_STORE)) {
        db.createObjectStore(DB_STORE, { keyPath: "id", autoIncrement: true });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("queue_db_open_failed"));
  });

  const withStore = async (mode, callback) => {
    const db = await openQueueDb();
    try {
      await new Promise((resolve, reject) => {
        const tx = db.transaction(DB_STORE, mode);
        const store = tx.objectStore(DB_STORE);
        callback(store, resolve, reject);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error || new Error("queue_tx_failed"));
        tx.onabort = () => reject(tx.error || new Error("queue_tx_aborted"));
      });
    } finally {
      db.close();
    }
  };

  const listQueuedUploads = async () => {
    let records = [];
    await withStore("readonly", (store) => {
      const request = store.getAll();
      request.onsuccess = () => {
        records = Array.isArray(request.result) ? request.result : [];
      };
    });
    records.sort((a, b) => Number(a.createdAt || 0) - Number(b.createdAt || 0));
    return records;
  };

  const queueLength = async () => {
    let count = 0;
    await withStore("readonly", (store) => {
      const request = store.count();
      request.onsuccess = () => {
        count = Number(request.result || 0);
      };
    });
    return count;
  };

  const enqueueUpload = async (record) => {
    let id = null;
    await withStore("readwrite", (store) => {
      const request = store.add(record);
      request.onsuccess = () => {
        id = request.result;
      };
    });
    return id;
  };

  const removeUploadFromQueue = async (queueId) => {
    await withStore("readwrite", (store) => {
      store.delete(queueId);
    });
  };

  const safeJson = async (response) => {
    try {
      return await response.json();
    } catch (_err) {
      return {};
    }
  };

  const getCookie = (name) => {
    const cookieString = document.cookie || "";
    if (!cookieString) return "";
    const parts = cookieString.split(";").map((part) => part.trim());
    for (const part of parts) {
      if (!part.startsWith(`${name}=`)) continue;
      return decodeURIComponent(part.slice(name.length + 1));
    }
    return "";
  };

  const getFormCsrfToken = () => {
    const tokenInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return tokenInput ? String(tokenInput.value || "").trim() : "";
  };

  const fetchCsrfToken = async () => {
    const response = await fetch(csrfApiUrl, {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return "";
    const payload = await safeJson(response);
    return String(payload.csrf_token || "").trim();
  };

  const ensureCsrfToken = async ({ forceRefresh = false } = {}) => {
    if (!forceRefresh && cachedCsrfToken) return cachedCsrfToken;
    const tokenFromForm = getFormCsrfToken();
    if (!forceRefresh && tokenFromForm) {
      cachedCsrfToken = tokenFromForm;
      return cachedCsrfToken;
    }
    const tokenFromCookie = getCookie("csrftoken");
    if (!forceRefresh && tokenFromCookie) {
      cachedCsrfToken = tokenFromCookie;
      return cachedCsrfToken;
    }
    cachedCsrfToken = await fetchCsrfToken();
    return cachedCsrfToken;
  };

  const isRetryableUploadFailure = (statusCode) => {
    if (statusCode === 429) return true;
    if (statusCode >= 500) return true;
    return false;
  };

  const buildFormDataFromRecord = async (record) => {
    const data = new FormData();
    data.append("file", record.fileBlob, record.fileName || "upload.bin");
    if (record.stationLabel) data.append("station_label", record.stationLabel);
    if (record.processNote) data.append("process_note", record.processNote);
    if (record.note) data.append("note", record.note);
    if (record.shareWithClass) data.append("share_with_class", "1");
    const csrfToken = await ensureCsrfToken();
    if (csrfToken) data.append("csrfmiddlewaretoken", csrfToken);
    return data;
  };

  const tryUploadRecord = async (record, { retryCsrf = true } = {}) => {
    const csrfToken = await ensureCsrfToken();
    const headers = { "X-Requested-With": "XMLHttpRequest" };
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
    const bodyPayload = await buildFormDataFromRecord(record);

    try {
      const response = await fetch(uploadApiUrl, {
        method: "POST",
        credentials: "same-origin",
        headers,
        body: bodyPayload,
      });
      const payload = await safeJson(response);
      if (response.ok && payload.ok) return { ok: true, payload };

      if (response.status === 403 && retryCsrf) {
        await ensureCsrfToken({ forceRefresh: true });
        return tryUploadRecord(record, { retryCsrf: false });
      }
      return {
        ok: false,
        retry: typeof payload.retry === "boolean"
          ? payload.retry
          : isRetryableUploadFailure(response.status),
        message: String(payload.message || i18n.uploadFailed),
      };
    } catch (_err) {
      return {
        ok: false,
        retry: true,
        message: i18n.syncError,
      };
    }
  };

  const buildUploadRecordFromForm = () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return null;
    const stationField = form.querySelector('[name="station_label"]');
    const processNoteField = form.querySelector('[name="process_note"]');
    const noteField = form.querySelector('[name="note"]');
    const publishField = form.querySelector('[name="share_with_class"]');
    const normalize = (value, max = 2000) => String(value || "").trim().slice(0, max);
    return {
      materialId: Number(body.getAttribute("data-material-id") || 0),
      classId: Number(body.getAttribute("data-class-id") || 0),
      studentId: Number(body.getAttribute("data-student-id") || 0),
      fileName: String(file.name || "upload.bin"),
      fileBlob: file,
      stationLabel: normalize(stationField ? stationField.value : "", 80),
      processNote: normalize(processNoteField ? processNoteField.value : "", 2000),
      note: normalize(noteField ? noteField.value : "", 2000),
      shareWithClass: Boolean(publishField && publishField.checked),
      createdAt: Date.now(),
    };
  };

  const refreshQueuePanel = async (preferredMessage = "") => {
    if (!queueSupported) return;
    const count = await queueLength();
    const message = preferredMessage || (count > 0 ? renderPendingCount(count) : i18n.queueNone);
    updateQueueStatus(message, { count });
  };

  const requestBackgroundSync = async () => {
    if (!navigator.serviceWorker || !("SyncManager" in window)) return;
    try {
      const registration = await navigator.serviceWorker.ready;
      if (!registration || !registration.sync) return;
      await registration.sync.register(SW_SYNC_TAG);
    } catch (_err) {
      // Ignore sync registration failures; manual/interval retry still works.
    }
  };

  const flushQueue = async ({ manual = false } = {}) => {
    if (!queueSupported || isFlushingQueue) return;
    isFlushingQueue = true;
    if (manual) setRetryEnabled(false);
    try {
      const queued = await listQueuedUploads();
      if (!queued.length) {
        await refreshQueuePanel();
        return;
      }
      updateQueueStatus(i18n.syncing, { count: queued.length });

      let syncedAny = false;
      for (const item of queued) {
        const result = await tryUploadRecord(item);
        if (result.ok) {
          await removeUploadFromQueue(item.id);
          syncedAny = true;
          continue;
        }
        if (!result.retry) {
          await removeUploadFromQueue(item.id);
          updateQueueStatus(result.message || i18n.uploadFailed, { count: await queueLength() });
        }
      }
      const remainingCount = await queueLength();
      if (remainingCount > 0) {
        updateQueueStatus(renderPendingCount(remainingCount), { count: remainingCount });
      } else {
        updateQueueStatus(syncedAny ? i18n.synced : i18n.queueNone, { count: 0 });
      }
    } finally {
      isFlushingQueue = false;
      if (manual) setRetryEnabled(true);
    }
  };

  const onFormSubmit = async (event) => {
    if (!queueSupported) return;
    const uploadRecord = buildUploadRecordFromForm();
    if (!uploadRecord) return;
    event.preventDefault();

    const uploadNow = await tryUploadRecord(uploadRecord);
    if (uploadNow.ok) {
      const redirectTo = String((uploadNow.payload && uploadNow.payload.redirect_url) || "").trim();
      if (redirectTo) {
        window.location.assign(redirectTo);
        return;
      }
      updateQueueStatus(i18n.uploadSaved, { count: await queueLength() });
      return;
    }
    if (!uploadNow.retry) {
      updateQueueStatus(uploadNow.message || i18n.uploadFailed, { count: await queueLength() });
      return;
    }

    await enqueueUpload(uploadRecord);
    fileInput.value = "";
    await refreshQueuePanel(i18n.queued);
    await requestBackgroundSync();
  };

  const initServiceWorker = async () => {
    if (!navigator.serviceWorker || !window.isSecureContext) return;
    try {
      await navigator.serviceWorker.register(SW_URL, { scope: "/" });
    } catch (_err) {
      // Ignore registration errors in unsupported/self-hosted browser contexts.
    }
  };

  if (!queueSupported) {
    if (queuePanel) queuePanel.classList.add("queue-panel--disabled");
    if (retryButton) retryButton.hidden = true;
    return;
  }

  if (retryButton) {
    retryButton.addEventListener("click", () => {
      flushQueue({ manual: true });
    });
  }
  form.addEventListener("submit", (event) => {
    onFormSubmit(event);
  });
  window.addEventListener("online", () => {
    flushQueue();
  });
  if (navigator.serviceWorker) {
    navigator.serviceWorker.addEventListener("message", (event) => {
      const payload = event.data || {};
      if (payload.type === "classhub-flush-upload-queue") flushQueue();
    });
  }

  window.setInterval(() => {
    if (document.visibilityState === "visible") flushQueue();
  }, Number.isFinite(syncIntervalMs) && syncIntervalMs > 10000 ? syncIntervalMs : 90000);

  initServiceWorker();
  refreshQueuePanel();
  flushQueue();
})();
