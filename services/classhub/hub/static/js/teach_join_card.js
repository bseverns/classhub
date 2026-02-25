(function () {
  const copyBtn = document.querySelector("[data-copy-value]");
  const printBtn = document.querySelector("[data-print-page]");
  const status = document.getElementById("copy-status");

  if (printBtn) {
    printBtn.addEventListener("click", () => {
      window.print();
    });
  }

  if (!copyBtn || !status) return;
  copyBtn.addEventListener("click", async () => {
    const text = copyBtn.getAttribute("data-copy-value") || "";
    if (!text) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const input = document.createElement("input");
        input.value = text;
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        document.body.removeChild(input);
      }
      status.textContent = "Copied class code.";
    } catch (_err) {
      status.textContent = "Copy failed. Highlight and copy the code manually.";
    }
  });
})();
