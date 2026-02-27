(function () {
  const ICON_ENTRIES = [
    ["A", "🐶", "Dog"],
    ["B", "🐱", "Cat"],
    ["C", "🐰", "Rabbit"],
    ["D", "🦊", "Fox"],
    ["E", "🐻", "Bear"],
    ["F", "🐼", "Panda"],
    ["G", "🐸", "Frog"],
    ["H", "🐵", "Monkey"],
    ["J", "🦁", "Lion"],
    ["K", "🐯", "Tiger"],
    ["L", "🐨", "Koala"],
    ["M", "🐮", "Cow"],
    ["N", "🐷", "Pig"],
    ["P", "🐔", "Chicken"],
    ["Q", "🦆", "Duck"],
    ["R", "🐧", "Penguin"],
    ["S", "🐢", "Turtle"],
    ["T", "🐙", "Octopus"],
    ["U", "🐳", "Whale"],
    ["V", "🦋", "Butterfly"],
    ["W", "🐞", "Ladybug"],
    ["X", "🌟", "Star"],
    ["Y", "☀️", "Sun"],
    ["Z", "🌈", "Rainbow"],
    ["2", "🍎", "Apple"],
    ["3", "🍌", "Banana"],
    ["4", "🍇", "Grapes"],
    ["5", "🍒", "Cherry"],
    ["6", "🍉", "Watermelon"],
    ["7", "🥕", "Carrot"],
    ["8", "🍪", "Cookie"],
    ["9", "⚽", "Ball"],
  ];

  const BY_CODE = new Map(ICON_ENTRIES.map(([code, icon, label]) => [code, { code, icon, label }]));

  const normalizeCode = (raw) => String(raw || "").toUpperCase().replace(/[^A-Z0-9]/g, "");

  const tokensFor = (raw) => {
    const value = normalizeCode(raw);
    return value.split("").map((code) => {
      const entry = BY_CODE.get(code);
      if (entry) return entry;
      return { code, icon: "□", label: code };
    });
  };

  const renderIconString = (raw, separator = " ") => tokensFor(raw).map((token) => token.icon).join(separator);

  const renderLabelString = (raw, separator = ", ") => tokensFor(raw).map((token) => token.label).join(separator);

  const buildIconBank = (container, onSelect) => {
    if (!container) return;
    container.innerHTML = "";
    ICON_ENTRIES.forEach(([code, icon, label]) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "icon-bank-btn";
      btn.setAttribute("data-code", code);
      btn.setAttribute("aria-label", `Add ${label}`);
      btn.title = `${label} (${code})`;
      btn.innerHTML = `<span class="icon-bank-glyph" aria-hidden="true">${icon}</span><span class="icon-bank-code" aria-hidden="true">${code}</span>`;
      btn.addEventListener("click", () => onSelect(code));
      container.appendChild(btn);
    });
  };

  window.ClassHubReturnCodeIcons = {
    normalizeCode,
    tokensFor,
    renderIconString,
    renderLabelString,
    buildIconBank,
  };
})();
