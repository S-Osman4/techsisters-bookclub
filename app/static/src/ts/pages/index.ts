// app/static/src/ts/pages/index.ts
import { showToast } from "../toast.js";

/**
 * Landing page — handles the access code form HTMX response.
 * The form itself is in modals/_access_code_modal.html.
 * On success, redirect to dashboard.
 * On error, show inline message inside #code-result.
 */

function handleCodeVerifyResponse(evt: Event): void {
  const event = evt as CustomEvent<{
    target: HTMLElement;
    xhr: XMLHttpRequest;
    requestConfig: { path: string };
  }>;

  const { target, xhr, requestConfig } = event.detail;

  // Only handle verify-code responses
  if (requestConfig.path !== "/auth/verify-code") return;
  if (target.id !== "code-result") return;

  if (xhr.status >= 200 && xhr.status < 300) {
    try {
      const data = JSON.parse(xhr.responseText) as {
        success?: boolean;
        message?: string;
      };
      if (data.success) {
        showToast(data.message ?? "Code verified. Welcome!", "success");
        setTimeout(() => {
          window.location.href = "/dashboard";
        }, 800);
      }
    } catch {
      // Non-JSON — handled globally
    }
  }
}

function handleCodeVerifyError(evt: Event): void {
  const event = evt as CustomEvent<{
    xhr: XMLHttpRequest;
    requestConfig: { path: string };
  }>;

  if (event.detail.requestConfig.path !== "/auth/verify-code") return;

  const resultEl = document.getElementById("code-result");
  if (!resultEl) return;

  try {
    const data = JSON.parse(event.detail.xhr.response) as {
      detail?: string;
    };
    resultEl.innerHTML = `
      <p class="text-sm text-red-600 mt-1">
        ${data.detail ?? "Invalid code. Please try again."}
      </p>`;
  } catch {
    resultEl.innerHTML = `
      <p class="text-sm text-red-600 mt-1">
        Something went wrong. Please try again.
      </p>`;
  }
}

document.addEventListener("htmx:afterSwap", handleCodeVerifyResponse);
document.addEventListener("htmx:responseError", handleCodeVerifyError);
