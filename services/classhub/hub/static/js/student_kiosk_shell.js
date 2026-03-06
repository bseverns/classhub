(function () {
  const body = document.body || document.documentElement;
  if (!body) return;

  const kioskFeatureEnabled = String(body.getAttribute("data-kiosk-shell-enabled") || "0").trim() === "1";
  const kioskModeEnabled = String(body.getAttribute("data-kiosk-mode") || "0").trim() === "1";
  if (!kioskFeatureEnabled || !kioskModeEnabled) return;

  const kioskHomeUrl = String(body.getAttribute("data-kiosk-home-url") || "/student?kiosk=1").trim();
  const kioskSwUrl = String(body.getAttribute("data-kiosk-sw-url") || "/student-upload-sync-sw.js").trim();
  const statusEl = document.getElementById("kiosk-shell-status");

  const i18nBlocked = String(
    body.getAttribute("data-i18n-kiosk-blocked") ||
    "Kiosk mode keeps navigation inside join, class, and upload routes.",
  ).trim();

  const allowedPath = (pathname) => {
    const path = String(pathname || "").trim();
    if (!path) return false;
    if (
      path === "/" ||
      path === "/join" ||
      path === "/student" ||
      path === "/student/return-code" ||
      path === "/student/micro-check" ||
      path === "/logout" ||
      path === "/privacy" ||
      path === "/trust" ||
      path === "/student-upload-sync-sw.js" ||
      path === "/student-shell.webmanifest"
    ) {
      return true;
    }
    if (path.startsWith("/invite/")) return true;
    if (path.startsWith("/course/")) return true;
    if (path.startsWith("/lesson-video/")) return true;
    if (path.startsWith("/lesson-asset/")) return true;
    if (path.startsWith("/api/v1/student/")) return true;
    if (path.startsWith("/static/")) return true;
    if (path.startsWith("/i18n/")) return true;
    if (/^\/material\/\d+\/upload$/.test(path)) return true;
    if (/^\/submission\/\d+\/download$/.test(path)) return true;
    if (/^\/student\/submission\/\d+\/publish$/.test(path)) return true;
    return false;
  };

  const showStatus = (message) => {
    if (!statusEl) return;
    statusEl.textContent = message;
  };

  const enforceCurrentLocation = () => {
    if (allowedPath(window.location.pathname)) return;
    window.location.replace(kioskHomeUrl);
  };

  body.classList.add("student-kiosk-mode");
  document.querySelectorAll("[data-kiosk-hide]").forEach((el) => {
    el.hidden = true;
    el.setAttribute("aria-hidden", "true");
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const anchor = target.closest("a[href]");
    if (!anchor) return;
    if (anchor.hasAttribute("download")) return;
    if (anchor.getAttribute("target") === "_blank") return;

    let nextUrl;
    try {
      nextUrl = new URL(anchor.getAttribute("href") || "", window.location.origin);
    } catch (_err) {
      return;
    }
    if (nextUrl.origin !== window.location.origin) return;
    if (allowedPath(nextUrl.pathname)) return;

    event.preventDefault();
    showStatus(i18nBlocked);
  });

  document.addEventListener("submit", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLFormElement)) return;
    if (!target.action) return;

    let actionUrl;
    try {
      actionUrl = new URL(target.action, window.location.origin);
    } catch (_err) {
      return;
    }
    if (actionUrl.origin !== window.location.origin) return;
    if (allowedPath(actionUrl.pathname)) return;

    event.preventDefault();
    showStatus(i18nBlocked);
  });

  if (navigator.serviceWorker && window.isSecureContext) {
    navigator.serviceWorker.register(kioskSwUrl, { scope: "/" }).catch(() => {
      // Best-effort registration only; kiosk shell still runs without SW support.
    });
  }

  enforceCurrentLocation();
})();
