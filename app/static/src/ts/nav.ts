// app/static/src/ts/nav.ts

/**
 * Mobile navigation menu toggle.
 * Closes on outside click and on resize to desktop width.
 */
export function initNav(): void {
  const menuBtn = document.getElementById("mobile-menu-btn");
  const menu = document.getElementById("mobile-menu");
  const menuIcon = document.getElementById("menu-icon");
  const closeIcon = document.getElementById("close-icon");

  if (!menuBtn || !menu) return;

  function openMenu(): void {
    menu!.classList.remove("hidden");
    menuIcon?.classList.add("hidden");
    closeIcon?.classList.remove("hidden");
    menuBtn!.setAttribute("aria-expanded", "true");
  }

  function closeMenu(): void {
    menu!.classList.add("hidden");
    menuIcon?.classList.remove("hidden");
    closeIcon?.classList.add("hidden");
    menuBtn!.setAttribute("aria-expanded", "false");
  }

  function isOpen(): boolean {
    return !menu!.classList.contains("hidden");
  }

  menuBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    isOpen() ? closeMenu() : openMenu();
  });

  // Close on outside click
  document.addEventListener("click", (e) => {
    if (isOpen() && !menu!.contains(e.target as Node)) {
      closeMenu();
    }
  });

  // Close when resizing to desktop
  window.addEventListener("resize", () => {
    if (window.innerWidth >= 768 && isOpen()) {
      closeMenu();
    }
  });

  // Close on Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && isOpen()) {
      closeMenu();
    }
  });
}
