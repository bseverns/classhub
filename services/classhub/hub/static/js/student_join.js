(function () {
  const msg = document.getElementById("msg");
  const joinForm = document.getElementById("join-form");
  const joinBtn = document.getElementById("join");
  const codeInput = document.getElementById("code");
  const nameInput = document.getElementById("name");
  const returnCodeInput = document.getElementById("return_code");
  const inviteTokenInput = document.getElementById("invite_token");
  const iconToggleBtn = document.getElementById("return-code-icon-toggle");
  const clearReturnCodeBtn = document.getElementById("return-code-clear");
  const iconPreview = document.getElementById("return-code-icon-preview");
  const iconBank = document.getElementById("return-code-icon-bank");
  const iconTools = window.ClassHubReturnCodeIcons || null;
  const i18nSource = document.body || document.documentElement;

  if (!msg || !joinForm || !joinBtn || !codeInput || !nameInput || !returnCodeInput) return;

  const readI18n = (key, fallback) => {
    const value = i18nSource ? String(i18nSource.getAttribute(`data-i18n-${key}`) || "").trim() : "";
    return value || fallback;
  };
  const i18n = {
    iconCodePrefix: readI18n("icon-code-prefix", "Icon code:"),
    keypadShow: readI18n("keypad-show", "Show icon keypad"),
    keypadHide: readI18n("keypad-hide", "Hide icon keypad"),
    errInvalidCode: readI18n("err-invalid-code", "That class code is not recognized."),
    errInvalidReturnCode: readI18n("err-invalid-return-code", "That return code is not valid for this class."),
    errReturnCodeRequired: readI18n("err-return-code-required", "Enter your return code to rejoin this saved name."),
    errClassLocked: readI18n("err-class-locked", "This class is locked right now."),
    errEnrollmentClosed: readI18n("err-enrollment-closed", "Enrollment for this class is closed."),
    errInviteRequired: readI18n("err-invite-required", "This class accepts joins by invite link only."),
    errMissingFields: readI18n("err-missing-fields", "Please enter a class code and your name."),
    errNameRejectedFallback: readI18n(
      "err-name-rejected-fallback",
      "Please use a nickname or display name instead of personal information.",
    ),
    errInviteInvalid: readI18n("err-invite-invalid", "That invite link is not valid."),
    errInviteInactive: readI18n("err-invite-inactive", "That invite link is disabled."),
    errInviteExpired: readI18n("err-invite-expired", "That invite link has expired."),
    errInviteSeatCap: readI18n(
      "err-invite-seat-cap",
      "This invite is full right now. Ask your teacher for a new invite link.",
    ),
    errRateLimited: readI18n("err-rate-limited", "Too many join attempts. Wait a minute and try again."),
    errSiteModeRestrictedFallback: readI18n("err-site-mode-restricted-fallback", "Joining is temporarily unavailable."),
    errSecurityBlocked: readI18n("err-security-blocked", "Security check blocked the join request. Reload and try again."),
    errServer: readI18n("err-server", "Server error while joining. Please try again in a moment."),
    errGeneric: readI18n("err-generic", "Could not join. Try again."),
    errNetwork: readI18n("err-network", "Network error. Please try again."),
  };

  const showErr = (text) => {
    msg.textContent = text;
    msg.classList.remove("warning");
    msg.style.display = "block";
    msg.focus();
  };

  const showWarning = (text) => {
    msg.textContent = text;
    msg.classList.add("warning");
    msg.style.display = "block";
  };

  // Django CSRF: read csrftoken cookie and send it as X-CSRFToken.
  // This keeps CSRF protection enabled without requiring a full form POST.
  const getCookie = (name) => {
    const cookies = document.cookie ? document.cookie.split("; ") : [];
    for (const cookie of cookies) {
      const idx = cookie.indexOf("=");
      if (idx === -1) continue;
      const k = cookie.slice(0, idx);
      const v = cookie.slice(idx + 1);
      if (k === name) return decodeURIComponent(v);
    }
    return "";
  };

  const csrfToken = () => getCookie("csrftoken") || "";
  const maxReturnCodeLength = Math.max(1, Number(returnCodeInput.getAttribute("maxlength") || "12"));
  const normalizeReturnCode = (value) => {
    if (iconTools && iconTools.normalizeCode) return iconTools.normalizeCode(value).slice(0, maxReturnCodeLength);
    return String(value || "").trim().toUpperCase().slice(0, maxReturnCodeLength);
  };
  const updateReturnCodePreview = () => {
    if (!iconPreview) return;
    const normalized = normalizeReturnCode(returnCodeInput.value);
    returnCodeInput.value = normalized;
    if (!normalized) {
      iconPreview.textContent = "";
      iconPreview.removeAttribute("aria-label");
      return;
    }
    if (iconTools && iconTools.renderIconString) {
      iconPreview.textContent = iconTools.renderIconString(normalized);
      if (iconTools.renderLabelString) {
        iconPreview.setAttribute("aria-label", `${i18n.iconCodePrefix} ${iconTools.renderLabelString(normalized)}`);
      }
      return;
    }
    iconPreview.textContent = normalized;
  };
  const setIconBankVisible = (visible) => {
    if (!iconBank) return;
    iconBank.classList.toggle("hidden", !visible);
    if (iconToggleBtn) {
      iconToggleBtn.setAttribute("aria-expanded", visible ? "true" : "false");
      iconToggleBtn.textContent = visible ? i18n.keypadHide : i18n.keypadShow;
    }
  };

  if (iconTools && iconBank && iconTools.buildIconBank) {
    iconTools.buildIconBank(iconBank, (code) => {
      const current = normalizeReturnCode(returnCodeInput.value);
      if (current.length >= maxReturnCodeLength) return;
      returnCodeInput.value = `${current}${code}`;
      updateReturnCodePreview();
      returnCodeInput.focus();
    });
  } else if (iconToggleBtn) {
    iconToggleBtn.classList.add("hidden");
  }

  if (iconToggleBtn) {
    iconToggleBtn.addEventListener("click", () => {
      const isOpen = iconBank && !iconBank.classList.contains("hidden");
      setIconBankVisible(!isOpen);
    });
  }
  if (clearReturnCodeBtn) {
    clearReturnCodeBtn.addEventListener("click", () => {
      returnCodeInput.value = "";
      updateReturnCodePreview();
      returnCodeInput.focus();
    });
  }
  returnCodeInput.addEventListener("input", updateReturnCodePreview);
  updateReturnCodePreview();

  const params = new URLSearchParams(window.location.search || "");
  const prefillCode = (params.get("class_code") || params.get("code") || "").trim();
  if (prefillCode) {
    codeInput.value = prefillCode;
    nameInput.focus();
  }

  joinForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    msg.style.display = "none";
    const class_code = (codeInput.value || "").trim();
    const display_name = (nameInput.value || "").trim();
    const return_code = normalizeReturnCode(returnCodeInput.value);
    const invite_token = inviteTokenInput ? (inviteTokenInput.value || "").trim() : "";

    joinBtn.disabled = true;
    joinBtn.setAttribute("aria-busy", "true");

    try {
      const res = await fetch("/join", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
        },
        credentials: "same-origin",
        body: JSON.stringify({ class_code, display_name, return_code, invite_token }),
      });

      if (!res.ok) {
        const contentType = (res.headers.get("content-type") || "").toLowerCase();
        const data = contentType.includes("application/json") ? await res.json().catch(() => ({})) : {};
        const errorCode = data.error || "join_failed";
        if (errorCode === "invalid_code") return showErr(i18n.errInvalidCode);
        if (errorCode === "invalid_return_code") return showErr(i18n.errInvalidReturnCode);
        if (errorCode === "return_code_required") return showErr(i18n.errReturnCodeRequired);
        if (errorCode === "class_locked") return showErr(i18n.errClassLocked);
        if (errorCode === "class_enrollment_closed") return showErr(i18n.errEnrollmentClosed);
        if (errorCode === "invite_required") return showErr(i18n.errInviteRequired);
        if (errorCode === "missing_fields") return showErr(i18n.errMissingFields);
        if (errorCode === "name_rejected") return showErr(data.message || i18n.errNameRejectedFallback);
        if (errorCode === "invite_invalid") return showErr(i18n.errInviteInvalid);
        if (errorCode === "invite_inactive") return showErr(i18n.errInviteInactive);
        if (errorCode === "invite_expired") return showErr(i18n.errInviteExpired);
        if (errorCode === "invite_seat_cap_reached") return showErr(i18n.errInviteSeatCap);
        if (errorCode === "rate_limited") return showErr(i18n.errRateLimited);
        if (errorCode === "site_mode_restricted") return showErr(data.message || i18n.errSiteModeRestrictedFallback);
        if (res.status === 403) return showErr(i18n.errSecurityBlocked);
        if (res.status >= 500) return showErr(i18n.errServer);
        return showErr(i18n.errGeneric);
      }

      const data = await res.json().catch(() => ({}));
      if (data.name_warning) {
        showWarning(data.name_warning);
      }

      window.location.href = "/student";
    } catch (_err) {
      showErr(i18n.errNetwork);
    } finally {
      joinBtn.disabled = false;
      joinBtn.removeAttribute("aria-busy");
    }
  });
})();
