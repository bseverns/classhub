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

  document.body.appendChild(overlay);
  return overlay;
}

function getMermaidContainer(target) {
  if (!target || !target.closest) {
    return null;
  }
  return target.closest(".md-typeset .mermaid");
}

function findMermaidFromEvent(event) {
  if (event && typeof event.composedPath === "function") {
    var path = event.composedPath();
    for (var i = 0; i < path.length; i += 1) {
      var node = path[i];
      if (!node || !node.classList || !node.classList.contains("mermaid")) {
        continue;
      }
      if (node.closest && node.closest(".md-typeset")) {
        return node;
      }
    }
  }
  return getMermaidContainer(event ? event.target : null);
}

function openDiagramLightbox(container) {
  var diagramNode =
    container.querySelector("svg") || container.querySelector("img");
  if (!diagramNode) {
    return;
  }

  var overlay = ensureDiagramLightbox();
  var frame = overlay.querySelector(".diagram-lightbox__frame");
  if (!frame) {
    return;
  }

  frame.innerHTML = "";

  var clone = diagramNode.cloneNode(true);
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

function enhanceMermaidContainers(root) {
  var containers = root.querySelectorAll(".md-typeset .mermaid");
  containers.forEach(function (container) {
    container.classList.add("diagram-zoomable");
    container.setAttribute("role", "button");
    container.setAttribute("tabindex", "0");
    container.setAttribute(
      "aria-label",
      "Open diagram zoom view (press Enter or click)"
    );
  });
}

function bindDiagramLightboxOnce() {
  if (window.__diagramLightboxBound) {
    return;
  }
  window.__diagramLightboxBound = true;

  document.addEventListener(
    "click",
    function (event) {
    var overlay = document.getElementById("diagram-lightbox");
    if (
      overlay &&
      overlay.classList.contains("is-open") &&
      (event.target === overlay ||
        (event.target.classList &&
          event.target.classList.contains("diagram-lightbox__close")))
    ) {
      closeDiagramLightbox();
      return;
    }

      var container = findMermaidFromEvent(event);
    if (!container) {
      return;
    }

    if (event.target.closest("a")) {
      return;
    }

    openDiagramLightbox(container);
    },
    true
  );

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeDiagramLightbox();
      return;
    }

    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    var container = findMermaidFromEvent(event);
    if (!container) {
      return;
    }

    event.preventDefault();
    openDiagramLightbox(container);
  });
}

function observeMermaidContainers() {
  if (window.__diagramLightboxObserverBound || !document.body) {
    return;
  }
  window.__diagramLightboxObserverBound = true;

  var observer = new MutationObserver(function () {
    enhanceMermaidContainers(document);
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

function initDiagramLightbox() {
  if (!document.body) {
    return;
  }
  ensureDiagramLightbox();
  bindDiagramLightboxOnce();
  enhanceMermaidContainers(document);
  observeMermaidContainers();
}

if (typeof document$ !== "undefined" && document$.subscribe) {
  document$.subscribe(initDiagramLightbox);
} else if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDiagramLightbox);
} else {
  initDiagramLightbox();
}
