/** Dark is the hero theme; the choice persists in localStorage. */

const KEY = "avatar-theme";

export function initTheme(): void {
  const saved = localStorage.getItem(KEY);
  if (saved === "dark" || saved === "light") {
    document.documentElement.setAttribute("data-theme", saved);
  }
  syncIcon();
  document.getElementById("themeToggle")?.addEventListener("click", () => {
    const next =
      document.documentElement.getAttribute("data-theme") === "dark"
        ? "light"
        : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(KEY, next);
    syncIcon();
  });
}

function syncIcon(): void {
  const dark = document.documentElement.getAttribute("data-theme") === "dark";
  const moon = document.querySelector<HTMLElement>(".theme-moon");
  const sun = document.querySelector<HTMLElement>(".theme-sun");
  if (moon) moon.style.display = dark ? "" : "none";
  if (sun) sun.style.display = dark ? "none" : "";
}
