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

  if (!msg || !joinForm || !joinBtn || !codeInput || !nameInput || !returnCodeInput) return;

  const showErr = (text) => {
    msg.textContent = text;
    msg.style.display = "block";
    msg.focus();
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
        iconPreview.setAttribute("aria-label", `Icon code: ${iconTools.renderLabelString(normalized)}`);
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
      iconToggleBtn.textContent = visible ? "Hide icon keypad" : "Show icon keypad";
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
        if (errorCode === "invalid_code") return showErr("That class code is not recognized.");
        if (errorCode === "invalid_return_code") return showErr("That return code is not valid for this class.");
        if (errorCode === "return_code_required") return showErr("Enter your return code to rejoin this saved name.");
        if (errorCode === "class_locked") return showErr("This class is locked right now.");
        if (errorCode === "class_enrollment_closed") return showErr("Enrollment for this class is closed.");
        if (errorCode === "invite_required") return showErr("This class accepts joins by invite link only.");
        if (errorCode === "missing_fields") return showErr("Please enter a class code and your name.");
        if (errorCode === "invite_invalid") return showErr("That invite link is not valid.");
        if (errorCode === "invite_inactive") return showErr("That invite link is disabled.");
        if (errorCode === "invite_expired") return showErr("That invite link has expired.");
        if (errorCode === "invite_seat_cap_reached") return showErr("This invite is full right now. Ask your teacher for a new invite link.");
        if (errorCode === "rate_limited") return showErr("Too many join attempts. Wait a minute and try again.");
        if (errorCode === "site_mode_restricted") return showErr(data.message || "Joining is temporarily unavailable.");
        if (res.status === 403) return showErr("Security check blocked the join request. Reload and try again.");
        if (res.status >= 500) return showErr("Server error while joining. Please try again in a moment.");
        return showErr("Could not join. Try again.");
      }

      window.location.href = "/student";
    } catch (_err) {
      showErr("Network error. Please try again.");
    } finally {
      joinBtn.disabled = false;
      joinBtn.removeAttribute("aria-busy");
    }
  });
})();
