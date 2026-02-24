(() => {
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const seeded = (index, salt) => {
    const raw = Math.sin((index + 1) * salt) * 10000;
    return raw - Math.floor(raw);
  };

  const palettes = [
    ["rgba(255, 255, 255, 0.74)", "rgba(255, 255, 255, 0)"],
    ["rgba(154, 219, 232, 0.46)", "rgba(154, 219, 232, 0)"],
    ["rgba(193, 228, 202, 0.42)", "rgba(193, 228, 202, 0)"],
    ["rgba(178, 205, 239, 0.4)", "rgba(178, 205, 239, 0)"],
  ];

  const buildOrbs = () => {
    const body = document.body;
    if (!body || !body.classList.contains("glass-theme")) return;
    if (body.classList.contains("teacher-comfort")) {
      const existing = document.getElementById("glass-bg-orbs");
      if (existing) existing.remove();
      return;
    }

    const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 1200;
    const count = clamp(Math.round(viewportWidth / 220), 3, 8);
    const minSize = clamp(Math.round(viewportWidth * 0.14), 120, 210);
    const maxSize = clamp(Math.round(viewportWidth * 0.34), 220, 520);

    let layer = document.getElementById("glass-bg-orbs");
    if (!layer) {
      layer = document.createElement("div");
      layer.id = "glass-bg-orbs";
      layer.className = "glass-bg-orbs";
      body.prepend(layer);
    }

    layer.innerHTML = "";
    for (let i = 0; i < count; i += 1) {
      const orb = document.createElement("span");
      orb.className = "glass-bg-orb";

      const size = Math.round(minSize + seeded(i, 12.9898) * (maxSize - minSize));
      const left = -12 + seeded(i, 78.233) * 124;
      const top = -16 + seeded(i, 39.425) * 132;
      const opacity = 0.32 + seeded(i, 27.193) * 0.34;
      const focalX = Math.round(22 + seeded(i, 9.173) * 56);
      const focalY = Math.round(18 + seeded(i, 3.917) * 60);
      const palette = palettes[i % palettes.length];

      orb.style.width = `${size}px`;
      orb.style.height = `${size}px`;
      orb.style.left = `${left}%`;
      orb.style.top = `${top}%`;
      orb.style.opacity = opacity.toFixed(2);
      orb.style.background = `radial-gradient(circle at ${focalX}% ${focalY}%, ${palette[0]}, ${palette[1]})`;

      layer.appendChild(orb);
    }
  };

  let resizeTimer = 0;
  const onResize = () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(buildOrbs, 180);
  };

  document.addEventListener("DOMContentLoaded", () => {
    buildOrbs();
    window.addEventListener("resize", onResize, { passive: true });
  });
})();
