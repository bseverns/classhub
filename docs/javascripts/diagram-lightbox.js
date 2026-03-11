function ensureDiagramLightbox() {
  var existing = document.getElementById("diagram-lightbox");
  if (existing) {
    return existing;
  }

  var overlay = document.createElement("div");
  overlay.id = "diagram-lightbox";
  overlay.className = "diagram-lightbox";
  overlay.setAttribute("aria-hidden", "true");
  overlay.innerHTML =
    '<div class="diagram-lightbox__content" role="dialog" aria-modal="true" aria-label="Diagram zoom view">' +
    '<button class="diagram-lightbox__close" type="button" aria-label="Close diagram zoom">&times;</button>' +
    '<div class="diagram-lightbox__frame"></div>' +
    "</div>";

  overlay.addEventListener("click", function (event) {
    if (
      event.target === overlay ||
      event.target.classList.contains("diagram-lightbox__close")
    ) {
      closeDiagramLightbox();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeDiagramLightbox();
    }
  });

  document.body.appendChild(overlay);
  return overlay;
}

function openDiagramLightbox(mermaidContainer) {
  var svg = mermaidContainer.querySelector("svg");
  if (!svg) {
    return;
  }

  var overlay = ensureDiagramLightbox();
  var frame = overlay.querySelector(".diagram-lightbox__frame");
  if (!frame) {
    return;
  }

  frame.innerHTML = "";

  var clone = svg.cloneNode(true);
  clone.removeAttribute("width");
  clone.removeAttribute("height");
  clone.style.removeProperty("width");
  clone.style.removeProperty("height");
  clone.style.removeProperty("max-width");
  frame.appendChild(clone);

  overlay.classList.add("is-open");
  overlay.setAttribute("aria-hidden", "false");
  document.body.classList.add("diagram-lightbox-open");
}

function closeDiagramLightbox() {
  var overlay = document.getElementById("diagram-lightbox");
  if (!overlay || !overlay.classList.contains("is-open")) {
    return;
  }

  var frame = overlay.querySelector(".diagram-lightbox__frame");
  if (frame) {
    frame.innerHTML = "";
  }

  overlay.classList.remove("is-open");
  overlay.setAttribute("aria-hidden", "true");
  document.body.classList.remove("diagram-lightbox-open");
}

function tryBindMermaidZoom(container) {
  if (container.dataset.diagramZoomBound === "1") {
    return true;
  }

  if (!container.querySelector("svg")) {
    return false;
  }

  container.dataset.diagramZoomBound = "1";
  container.classList.add("diagram-zoomable");
  container.setAttribute("role", "button");
  container.setAttribute("tabindex", "0");
  container.setAttribute(
    "aria-label",
    "Open diagram zoom view (press Enter or click)"
  );

  container.addEventListener("click", function (event) {
    if (event.target.closest("a")) {
      return;
    }
    openDiagramLightbox(container);
  });

  container.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    event.preventDefault();
    openDiagramLightbox(container);
  });

  if (container.__diagramObserver) {
    container.__diagramObserver.disconnect();
    container.__diagramObserver = null;
  }

  return true;
}

function bindMermaidZoom(root) {
  var containers = root.querySelectorAll(".md-typeset .mermaid");
  containers.forEach(function (container) {
    if (tryBindMermaidZoom(container)) {
      return;
    }
    if (container.__diagramObserver) {
      return;
    }
    var observer = new MutationObserver(function () {
      tryBindMermaidZoom(container);
    });
    observer.observe(container, { childList: true, subtree: true });
    container.__diagramObserver = observer;
  });
}

document$.subscribe(function () {
  ensureDiagramLightbox();
  bindMermaidZoom(document);
});
