(function () {
  const status = document.getElementById("copy-status");
  const copyButtons = document.querySelectorAll("[data-copy-value], [data-copy-secret-target]");
  const toggleButtons = document.querySelectorAll("[data-secret-target]");
  const classId = String((document.body && document.body.dataset.classId) || "").trim();
  const returnCodeBaseUrl = classId ? `/teach/class/${encodeURIComponent(classId)}/student` : "";
  const returnCodeCache = new Map();
  const returnCodePromises = new Map();

  const setStatus = (message) => {
    if (status) status.textContent = message;
  };

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = String(form.getAttribute("data-confirm") || "").trim();
      if (message && !window.confirm(message)) event.preventDefault();
    });
  });

  const studentIdFor = (el) => {
    if (!el) return "";
    return String(el.getAttribute("data-return-code-student-id") || "").trim();
  };

  const fetchReturnCode = async (studentId) => {
    if (!returnCodeBaseUrl) throw new Error("missing_class_id");
    if (!studentId) throw new Error("missing_student_id");
    if (returnCodeCache.has(studentId)) return returnCodeCache.get(studentId) || "";
    if (!returnCodePromises.has(studentId)) {
      returnCodePromises.set(
        studentId,
        fetch(`${returnCodeBaseUrl}/${encodeURIComponent(studentId)}/return-code`, {
          method: "GET",
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        })
          .then(async (resp) => {
            if (!resp.ok) throw new Error("return_code_unavailable");
            const payload = await resp.json();
            const value = (payload && payload.return_code ? String(payload.return_code) : "").trim();
            if (!value) throw new Error("missing_return_code");
            returnCodeCache.set(studentId, value);
            return value;
          })
          .finally(() => {
            if (!returnCodeCache.has(studentId)) returnCodePromises.delete(studentId);
          })
      );
    }
    return returnCodePromises.get(studentId);
  };

  const maskFor = (value) => "•".repeat(Math.max(value.length, 6));
  const setMasked = (el) => {
    const studentId = studentIdFor(el);
    const plain = studentId ? (returnCodeCache.get(studentId) || "") : "";
    el.textContent = maskFor(plain);
    el.setAttribute("data-shown", "0");
  };
  const setShown = async (el) => {
    const plain = await fetchReturnCode(studentIdFor(el));
    el.textContent = plain || maskFor("");
    el.setAttribute("data-shown", "1");
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
        const target = document.getElementById(btn.getAttribute("data-copy-secret-target") || "");
        try {
          value = await fetchReturnCode(studentIdFor(target));
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
