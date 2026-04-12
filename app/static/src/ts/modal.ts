// app/static/src/ts/modal.ts

/**
 * Generic modal helpers.
 * Call openModal / closeModal with the overlay element ID.
 */

export function openModal(id: string): void {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("hidden");
  el.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

export function closeModal(id: string): void {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add("hidden");
  el.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

/**
 * Initialise all modals on the page:
 * - Close on backdrop click
 * - Close on Escape key
 * - Close button wiring
 */
export function initModals(): void {
  // Backdrop click
  document.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains("modal-overlay")) {
      closeModal(target.id);
    }
  });

  // Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    document
      .querySelectorAll<HTMLElement>(".modal-overlay:not(.hidden)")
      .forEach((el) => closeModal(el.id));
  });
}

// Expose globally for inline onclick in templates
const g = window as unknown as Record<string, unknown>;
g["openModal"] = openModal;
g["closeModal"] = closeModal;
