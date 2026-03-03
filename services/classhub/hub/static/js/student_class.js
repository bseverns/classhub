(function () {
  const status = document.getElementById("copy-status");
  const i18nSource = document.body || document.documentElement;
  const iconTarget = document.getElementById("student-return-code-icons");
  const copyButtons = document.querySelectorAll("[data-copy-value], [data-copy-secret-target]");
  const toggleButtons = document.querySelectorAll("[data-secret-target]");
  const starterButtons = document.querySelectorAll("[data-starter-target][data-feedback-starter]");
  const returnCodeUrl = "/student/return-code";
  const iconTools = window.ClassHubReturnCodeIcons || null;
  let returnCodeValue = "";
  let returnCodePromise = null;

  const readI18n = (key, fallback) => {
    const value = i18nSource ? String(i18nSource.getAttribute(`data-i18n-${key}`) || "").trim() : "";
    return value || fallback;
  };
  const i18n = {
    showLabel: readI18n("show-label", "Show return code"),
    hideLabel: readI18n("hide-label", "Hide return code"),
    showButton: readI18n("show-button", "Show"),
    hideButton: readI18n("hide-button", "Hide"),
    returnCodeHiddenStatus: readI18n("status-return-code-hidden", "Return code hidden."),
    returnCodeShownStatus: readI18n("status-return-code-shown", "Return code shown."),
    returnCodeLoadError: readI18n(
      "status-return-code-load-error",
      "Could not load return code. Refresh and try again.",
    ),
    copySuccessStatus: readI18n("status-copy-success", "Copied to clipboard."),
    copyErrorStatus: readI18n("status-copy-error", "Copy failed. Please copy manually."),
    starterAddedStatus: readI18n("status-starter-added", "Sentence starter added."),
    iconCodePrefix: readI18n("icon-code-prefix", "Icon code: "),
  };

  const setStatus = (message) => {
    if (status) status.textContent = message;
  };

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = String(form.getAttribute("data-confirm") || "").trim();
      if (message && !window.confirm(message)) event.preventDefault();
    });
  });

  const fetchReturnCode = async () => {
    if (returnCodeValue) return returnCodeValue;
    if (!returnCodePromise) {
      returnCodePromise = fetch(returnCodeUrl, {
        method: "GET",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
        .then(async (resp) => {
          if (!resp.ok) throw new Error("return_code_unavailable");
          const payload = await resp.json();
          const value = (payload && payload.return_code ? String(payload.return_code) : "").trim();
          if (!value) throw new Error("missing_return_code");
          returnCodeValue = value;
          return value;
        })
        .finally(() => {
          if (!returnCodeValue) returnCodePromise = null;
        });
    }
    return returnCodePromise;
  };

  const maskFor = (value) => "•".repeat(Math.max(value.length, 6));
  const hideIconCode = () => {
    if (!iconTarget) return;
    iconTarget.textContent = "";
    iconTarget.classList.add("hidden");
    iconTarget.removeAttribute("aria-label");
  };
  const showIconCode = (value) => {
    if (!iconTarget || !value || !(iconTools && iconTools.renderIconString)) return;
    iconTarget.textContent = iconTools.renderIconString(value);
    if (iconTools.renderLabelString) {
      iconTarget.setAttribute("aria-label", `${i18n.iconCodePrefix}${iconTools.renderLabelString(value)}`);
    }
    iconTarget.classList.remove("hidden");
  };
  const setMasked = (el) => {
    el.textContent = maskFor(returnCodeValue);
    el.setAttribute("data-shown", "0");
    hideIconCode();
  };
  const setShown = async (el) => {
    const plain = await fetchReturnCode();
    el.textContent = plain || maskFor("");
    el.setAttribute("data-shown", "1");
    showIconCode(plain);
  };

  toggleButtons.forEach((btn) => {
    const target = document.getElementById(btn.getAttribute("data-secret-target") || "");
    if (!target) return;
    setMasked(target);
    btn.addEventListener("click", async () => {
      const shown = target.getAttribute("data-shown") === "1";
      const showLabel = btn.getAttribute("data-show-label") || i18n.showLabel;
      const hideLabel = btn.getAttribute("data-hide-label") || i18n.hideLabel;
      if (shown) {
        setMasked(target);
        btn.textContent = i18n.showButton;
        btn.setAttribute("aria-pressed", "false");
        btn.setAttribute("aria-label", showLabel);
        setStatus(i18n.returnCodeHiddenStatus);
      } else {
        try {
          await setShown(target);
          btn.textContent = i18n.hideButton;
          btn.setAttribute("aria-pressed", "true");
          btn.setAttribute("aria-label", hideLabel);
          setStatus(i18n.returnCodeShownStatus);
        } catch (_err) {
          setStatus(i18n.returnCodeLoadError);
        }
      }
    });
  });

  copyButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      let value = btn.getAttribute("data-copy-value") || "";
      if (!value) {
        try {
          value = await fetchReturnCode();
        } catch (_err) {
          setStatus(i18n.returnCodeLoadError);
          return;
        }
      }
      if (!value) return;
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(value);
        } else {
          const input = document.createElement("input");
          input.value = value;
          document.body.appendChild(input);
          input.select();
          document.execCommand("copy");
          document.body.removeChild(input);
        }
        setStatus(i18n.copySuccessStatus);
      } catch (_err) {
        setStatus(i18n.copyErrorStatus);
      }
    });
  });

  starterButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = String(btn.getAttribute("data-starter-target") || "").trim();
      const starter = String(btn.getAttribute("data-feedback-starter") || "").trim();
      const target = targetId ? document.getElementById(targetId) : null;
      if (!target || !starter) return;

      const prefix = target.value && target.value.trim() ? "\n" : "";
      const insertion = `${prefix}${starter} `;
      const hasSelection = typeof target.selectionStart === "number" && typeof target.selectionEnd === "number";
      if (hasSelection && typeof target.setRangeText === "function") {
        target.setRangeText(insertion, target.selectionStart, target.selectionEnd, "end");
      } else {
        target.value = `${target.value || ""}${insertion}`;
      }
      target.focus();
      target.dispatchEvent(new Event("input", { bubbles: true }));
      setStatus(i18n.starterAddedStatus);
    });
  });
})();
