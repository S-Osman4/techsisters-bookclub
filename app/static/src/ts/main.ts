// app/static/src/ts/main.ts
/**
 * Entry point — initialises all modules on DOMContentLoaded.
 * Import order matters: csrf before htmx-hooks.
 */
import { initCsrf } from "./csrf.js";
import { initNav } from "./nav.js";
import { initModals } from "./modal.js";
import { initHtmxHooks } from "./htmx-hooks.js";
import { initUrlErrors } from "./url-errors.js";
import { showToast } from "./toast.js";

document.addEventListener("DOMContentLoaded", () => {
  initCsrf(); // Must be first — injects X-CSRFToken into all HTMX requests
  initNav();
  initModals();
  initHtmxHooks();
  initUrlErrors();

  // Render any Lucide icons present on initial page load
  if (window.lucide) {
    window.lucide.createIcons();
  }
});

// Re-export showToast so templates can call window.showToast(...)
export { showToast };
