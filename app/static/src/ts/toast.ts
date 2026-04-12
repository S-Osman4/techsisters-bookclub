// app/static/src/ts/toast.ts
import type { ToastType } from "./types.js";

const ICONS: Record<ToastType, string> = {
  success: "check-circle",
  error: "x-circle",
  warning: "alert-triangle",
  info: "info",
};

const COLORS: Record<ToastType, string> = {
  success: "#4ECDC4",
  error: "#FF6B6B",
  warning: "#FFD93D",
  info: "#60A5FA",
};

let container: HTMLElement | null = null;

function getContainer(): HTMLElement {
  if (!container) {
    container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.style.cssText =
        "position:fixed;top:1.25rem;right:1.25rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;";
      document.body.appendChild(container);
    }
  }
  return container;
}

export function copyMeetingLink(link: string): void {
  navigator.clipboard.writeText(link).then(() => {
    // Reuse your existing showToast function
    showToast("Meeting link copied to clipboard", "success", 2000);
  }).catch(() => {
    showToast("Could not copy link. Please copy manually.", "warning");
  });
}

export function showToast(
  message: string,
  type: ToastType = "success",
  duration: number = 5000,
): void {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.style.backgroundColor = COLORS[type];
  toast.innerHTML = `
    <i data-lucide="${ICONS[type]}" style="width:18px;height:18px;flex-shrink:0;"></i>
    <span style="flex:1;">${message}</span>
    <button
      onclick="this.parentElement.remove()"
      style="background:none;border:none;color:white;cursor:pointer;
             padding:0;margin-left:0.5rem;font-size:1.2rem;line-height:1;opacity:0.8;"
      aria-label="Dismiss"
    >×</button>
  `;

  getContainer().appendChild(toast);

  // Re-render Lucide icons inside the toast
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // Auto-dismiss
  setTimeout(() => {
    toast.style.transition = "opacity 0.3s, transform 0.3s";
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Expose globally for inline onclick handlers in templates
(window as unknown as Record<string, unknown>)["showToast"] = showToast;
(window as unknown as Record<string, unknown>)["copyMeetingLink"] = copyMeetingLink;
