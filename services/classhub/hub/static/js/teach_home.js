(function () {
  const tabRoot = document.querySelector("[data-tabs]");
  if (tabRoot) {
    const tabs = Array.from(tabRoot.querySelectorAll("[role='tab']"));
    const panels = Array.from(tabRoot.querySelectorAll("[role='tabpanel']"));

    const activate = (tabId) => {
      tabs.forEach((tab) => {
        const active = tab.id === tabId;
        tab.setAttribute("aria-selected", active ? "true" : "false");
        tab.tabIndex = active ? 0 : -1;
      });
      panels.forEach((panel) => {
        const active = panel.getAttribute("aria-labelledby") === tabId;
        panel.hidden = !active;
      });
    };

    const initialTab = tabRoot.getAttribute("data-initial-tab") || "quick-actions";
    const initial = tabs.find((tab) => tab.id === `tab-${initialTab}`) || tabs[0];
    if (initial) activate(initial.id);

    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => activate(tab.id));
      tab.addEventListener("keydown", (event) => {
        if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
          event.preventDefault();
          const delta = event.key === "ArrowRight" ? 1 : -1;
          const next = (index + delta + tabs.length) % tabs.length;
          tabs[next].focus();
          activate(tabs[next].id);
        }
        if (event.key === "Home") {
          event.preventDefault();
          tabs[0].focus();
          activate(tabs[0].id);
        }
        if (event.key === "End") {
          event.preventDefault();
          tabs[tabs.length - 1].focus();
          activate(tabs[tabs.length - 1].id);
        }
      });
    });
  }

  const status = document.getElementById("copy-status");
  const buttons = document.querySelectorAll("[data-copy-value]");
  if (!status || !buttons.length) return;

  const copyText = async (text) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const input = document.createElement("input");
    input.value = text;
    document.body.appendChild(input);
    input.select();
    document.execCommand("copy");
    document.body.removeChild(input);
  };

  buttons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const value = btn.getAttribute("data-copy-value") || "";
      if (!value) return;
      try {
        await copyText(value);
        status.textContent = "Copied join code.";
      } catch (_err) {
        status.textContent = "Copy failed. Please copy manually.";
      }
    });
  });
})();
