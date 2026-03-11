function normalizeMermaidBlocks(root) {
  var blocks = root.querySelectorAll(".md-typeset .mermaid");
  blocks.forEach(function (block) {
    if (block.dataset.mermaidNormalized === "1") {
      return;
    }

    var normalized = block;

    if (block.tagName === "PRE") {
      var replacement = document.createElement("div");
      replacement.className = block.className;
      replacement.textContent = block.textContent.trim();
      block.replaceWith(replacement);
      normalized = replacement;
    } else {
      var directCode = block.querySelector(":scope > code");
      if (directCode) {
        block.textContent = directCode.textContent.trim();
      }
    }

    normalized.dataset.mermaidNormalized = "1";
  });
}

document$.subscribe(function () {
  if (typeof mermaid === "undefined") {
    return;
  }
  normalizeMermaidBlocks(document);
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    themeVariables: {
      fontSize: "22px",
    },
    flowchart: {
      useMaxWidth: true,
    },
    sequence: {
      useMaxWidth: true,
    },
    journey: {
      useMaxWidth: true,
    },
    gantt: {
      useMaxWidth: true,
    },
  });
  mermaid.parseError = function (error, hash) {
    console.error("[docs] Mermaid parse error", {
      path: window.location.pathname,
      error,
      hash,
    });
  };
  mermaid
    .run({
      querySelector: ".md-typeset .mermaid",
    })
    .catch(function (error) {
      console.error("[docs] Mermaid render failed", {
        path: window.location.pathname,
        error,
      });
    });
});
