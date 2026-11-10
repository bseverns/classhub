(function () {
  document.querySelectorAll("form.reading-level-picker").forEach(function (form) {
    if (form.classList.contains("is-js")) return;
    const select = form.querySelector("select");
    if (!select) return;
    form.classList.add("is-js");

    const initialValue = select.value;
    let keyboardChange = false;
    let submitted = false;

    function go() {
      if (submitted) return;
      submitted = true;
      form.submit();
    }

    // Mouse/touch pick: submit right away.
    select.addEventListener("pointerdown", function () {
      keyboardChange = false;
    });
    select.addEventListener("change", function () {
      if (!keyboardChange) go();
    });

    // Keyboard: arrowing through options must not reload the page on every key press.
    select.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        if (select.value !== initialValue) go();
        return;
      }
      if (event.key !== "Tab" && event.key !== "Escape") keyboardChange = true;
    });
    select.addEventListener("blur", function () {
      if (keyboardChange && select.value !== initialValue) go();
    });
  });
})();
