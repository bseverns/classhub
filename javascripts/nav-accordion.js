document$.subscribe(function () {
  var topLevelItems = Array.from(
    document.querySelectorAll(".md-sidebar--primary .md-nav--primary > .md-nav__list > .md-nav__item")
  );

  var topLevelToggles = topLevelItems
    .map(function (item) {
      return Array.from(item.children).find(function (child) {
        return child.classList && child.classList.contains("md-nav__toggle");
      });
    })
    .filter(Boolean);

  if (!topLevelToggles.length) {
    return;
  }

  var activeToggle = null;
  topLevelToggles.forEach(function (toggle) {
    var item = toggle.closest(".md-nav__item");
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
