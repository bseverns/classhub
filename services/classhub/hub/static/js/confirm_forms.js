(function () {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = String(form.getAttribute("data-confirm") || "").trim();
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
})();
