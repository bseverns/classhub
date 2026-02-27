(function () {
  const status = document.getElementById("copy-status");
  const iconTarget = document.getElementById("student-return-code-icons");
  const copyButtons = document.querySelectorAll("[data-copy-value], [data-copy-secret-target]");
  const toggleButtons = document.querySelectorAll("[data-secret-target]");
  const returnCodeUrl = "/student/return-code";
  const iconTools = window.ClassHubReturnCodeIcons || null;
  let returnCodeValue = "";
  let returnCodePromise = null;

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
      iconTarget.setAttribute("aria-label", `Icon code: ${iconTools.renderLabelString(value)}`);
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
      const showLabel = btn.getAttribute("data-show-label") || "Show return code";
      const hideLabel = btn.getAttribute("data-hide-label") || "Hide return code";
      if (shown) {
        setMasked(target);
        btn.textContent = "Show";
        btn.setAttribute("aria-pressed", "false");
        btn.setAttribute("aria-label", showLabel);
        setStatus("Return code hidden.");
      } else {
        try {
          await setShown(target);
          btn.textContent = "Hide";
          btn.setAttribute("aria-pressed", "true");
          btn.setAttribute("aria-label", hideLabel);
          setStatus("Return code shown.");
        } catch (_err) {
          setStatus("Could not load return code. Refresh and try again.");
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
          setStatus("Could not load return code. Refresh and try again.");
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
        setStatus("Copied to clipboard.");
      } catch (_err) {
        setStatus("Copy failed. Please copy manually.");
      }
    });
  });
})();
