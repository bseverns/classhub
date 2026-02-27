document$.subscribe(function () {
  var topLevelToggles = Array.from(
    document.querySelectorAll(
      ".md-sidebar--primary .md-nav--primary > .md-nav__list > .md-nav__item--nested > .md-nav__toggle"
    )
  );

  if (!topLevelToggles.length) {
    return;
  }

  var activeToggle = null;
  topLevelToggles.forEach(function (toggle) {
    var item = toggle.closest(".md-nav__item--nested");
    if (!item) return;
    if (item.classList.contains("md-nav__item--active") || item.querySelector(".md-nav__link--active")) {
      activeToggle = toggle;
    }
  });

  topLevelToggles.forEach(function (toggle) {
    if (activeToggle && toggle === activeToggle) {
      toggle.checked = true;
    } else {
      toggle.checked = false;
    }

    if (toggle.dataset.accordionBound === "1") {
      return;
    }
    toggle.dataset.accordionBound = "1";

    toggle.addEventListener("change", function () {
      if (!toggle.checked) return;
      topLevelToggles.forEach(function (other) {
        if (other !== toggle) {
          other.checked = false;
        }
      });
    });
  });
});
