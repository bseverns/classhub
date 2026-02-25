document$.subscribe(function () {
  if (typeof mermaid === "undefined") {
    return;
  }
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    themeVariables: {
      fontSize: "16px",
    },
    flowchart: {
      useMaxWidth: false,
    },
    sequence: {
      useMaxWidth: false,
    },
    journey: {
      useMaxWidth: false,
    },
    gantt: {
      useMaxWidth: false,
    },
  });
  mermaid.run({
    querySelector: ".mermaid",
  });
});
