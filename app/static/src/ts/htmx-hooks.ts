// app/static/src/ts/htmx-hooks.ts
import { showToast } from "./toast.js";

interface HtmxAfterRequestDetail {
  xhr: XMLHttpRequest;
  target: Element;
  elt: Element;
  requestConfig: { path: string };
}

interface HtmxResponseErrorDetail {
  xhr: XMLHttpRequest;
  requestConfig: { path: string };
}

/**
 * Wire up global HTMX event handlers:
 *
 * htmx:afterRequest  — Handle JSON success responses, HX-Redirect header
 * htmx:responseError — Show toast on 4xx/5xx
 * htmx:afterSwap     — Re-run Lucide icon registration
 */
export function initHtmxHooks(): void {
  // Re-render icons after every HTMX swap
  document.addEventListener("htmx:afterSwap", () => {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  });

  // Handle successful responses
  document.addEventListener("htmx:afterRequest", (evt: Event) => {
    const { xhr, target } = (evt as CustomEvent<HtmxAfterRequestDetail>)
      .detail;

    if (xhr.status >= 400) return;

    // Handle HX-Redirect header (login, register, logout)
    const redirect = xhr.getResponseHeader("HX-Redirect");
    if (redirect) {
      window.location.href = redirect;
      return;
    }

    // Handle JSON success responses
    const contentType = xhr.getResponseHeader("Content-Type") ?? "";
    if (!contentType.includes("application/json")) return;

    try {
      const data = JSON.parse(xhr.responseText) as {
        message?: string;
        success?: boolean;
        reload?: boolean;
      };

      if (data.message && xhr.status >= 200 && xhr.status < 300) {
        showToast(data.message, "success");

        // Clear the target div (e.g. result placeholders)
        if (target instanceof HTMLElement && target.id?.includes("result")) {
          target.innerHTML = "";
        }

        if (data.reload) {
          setTimeout(() => window.location.reload(), 1200);
        }
      }
    } catch {
      // Not JSON — ignore
    }
  });

  // Handle error responses
  document.addEventListener("htmx:responseError", (evt: Event) => {
    const { xhr } = (evt as CustomEvent<HtmxResponseErrorDetail>).detail;

    try {
      const data = JSON.parse(xhr.response) as {
        detail?: string;
      };
      const msg = data.detail ?? "An error occurred.";

      switch (xhr.status) {
        case 401:
          showToast("Please log in to continue.", "error");
          setTimeout(() => {
            window.location.href = "/login?error=login_required";
          }, 1500);
          break;
        case 403:
          showToast(msg, "warning");
          break;
        case 422:
          showToast(msg, "warning");
          break;
        case 429:
          showToast("Too many requests. Please wait a moment.", "warning");
          break;
        default:
          showToast(msg, "error");
      }
    } catch {
      if (xhr.status === 0) {
        showToast("Network error. Please check your connection.", "error");
      } else {
        showToast("An unexpected error occurred.", "error");
      }
    }
  });
}
