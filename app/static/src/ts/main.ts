// app/static/src/ts/main.ts
import { initCsrf } from "./csrf.js";

import { initNav } from "./nav.js";

import { initModals } from "./modal.js";

import { initHtmxHooks } from "./htmx-hooks.js";

import { initUrlErrors } from "./url-errors.js";

import { showToast } from "./toast.js";

// main.ts

/**
 * Apply the given theme to the document and update all theme icons.
 */
function applyTheme(theme: "dark" | "light"): void {
  const isDark = theme === "dark";
  document.documentElement.classList.toggle("dark", isDark);
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);

  // Update all sun icons (show in dark mode)
  document.querySelectorAll(".theme-icon-sun").forEach((el) => {
    el.classList.toggle("hidden", !isDark);
  });
  // Update all moon icons (show in light mode)
  document.querySelectorAll(".theme-icon-moon").forEach((el) => {
    el.classList.toggle("hidden", isDark);
  });
}

/**
 * Initialize theme on page load.
 */
function initTheme(): void {
  const saved = localStorage.getItem("theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark = saved === "dark" || (!saved && prefersDark);
  applyTheme(isDark ? "dark" : "light");
}

function initThemeToggle(): void {
  document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", toggleTheme);
  });
}

/**
 * Toggle between light and dark themes.
 * Exposed globally for onclick handlers.
 */
function toggleTheme(): void {
  const current = document.documentElement.getAttribute("data-theme");
  applyTheme(current === "dark" ? "light" : "dark");
}

// Expose toggleTheme globally (for inline onclick)
(window as any).toggleTheme = toggleTheme;

// Initialize theme when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initCsrf(); // your existing init
  initNav(); // your existing init
  initModals(); // your existing init
  initHtmxHooks(); // your existing init
  initUrlErrors(); // your existing init
  initTheme(); // <-- theme initialization
  initThemeToggle(); // <-- theme toggle button initialization
  if (window.lucide) window.lucide.createIcons();
});

export { showToast };
