(function () {
  const items = Array.from(document.querySelectorAll(".video-item"));
  if (!items.length) return;

  const closeItem = (item) => {
    const button = item.querySelector(".video-toggle");
    const panel = item.querySelector(".video-panel");
    if (!button || !panel) return;
    button.setAttribute("aria-expanded", "false");
    panel.hidden = true;

    const iframe = panel.querySelector("iframe[data-src]");
    if (iframe && iframe.src) {
      iframe.src = "";
    }

    const media = panel.querySelector("video");
    if (media) {
      try {
        media.pause();
      } catch (_err) {
        // ignore media pause errors
      }
    }
  };

  const openItem = (item) => {
    const button = item.querySelector(".video-toggle");
    const panel = item.querySelector(".video-panel");
    if (!button || !panel) return;

    items.forEach((other) => {
      if (other !== item) closeItem(other);
    });

    button.setAttribute("aria-expanded", "true");
    panel.hidden = false;

    const iframe = panel.querySelector("iframe[data-src]");
    if (iframe && !iframe.src) {
      iframe.src = iframe.dataset.src || "";
    }
  };

  items.forEach((item) => {
    const button = item.querySelector(".video-toggle");
    const panel = item.querySelector(".video-panel");
    if (!button || !panel) return;
    button.addEventListener("click", () => {
      const expanded = button.getAttribute("aria-expanded") === "true";
      if (expanded) {
        closeItem(item);
      } else {
        openItem(item);
      }
    });
  });
})();
