document$.subscribe(function () {
  if (typeof mermaid === "undefined") {
    return;
  }
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
      querySelector: ".mermaid",
    })
    .catch(function (error) {
      console.error("[docs] Mermaid render failed", {
        path: window.location.pathname,
        error,
      });
    });
});
