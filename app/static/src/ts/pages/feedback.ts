// app/static/src/ts/pages/feedback.ts
import { showToast } from "../toast.js";

/**
 * Feedback page.
 *
 * Handles:
 * - Character count for message textarea
 * - Success response — shows inline confirmation, resets form
 * - Error response — shows inline error message
 */

function initCharCount(): void {
  const textarea = document.getElementById(
    "feedback-message",
  ) as HTMLTextAreaElement | null;
  const counter = document.getElementById("char-count");
  const maxLength = 2000;

  if (!textarea || !counter) return;

  textarea.addEventListener("input", () => {
    const count = textarea.value.length;
    counter.textContent = String(count);
    counter.classList.toggle("text-red-500", count >= maxLength * 0.9);
  });
}

function handleFeedbackResponse(evt: Event): void {
  const event = evt as CustomEvent<{
    target: HTMLElement;
    xhr: XMLHttpRequest;
    elt: HTMLElement;
  }>;

  if (event.detail.target.id !== "feedback-result") return;
  const xhr = event.detail.xhr;

  if (xhr.status >= 200 && xhr.status < 300) {
    // Service returns an HTML fragment for HTMX to swap in
    // The swap already happened — just show a toast and reset form
    showToast("Feedback sent. Thank you!", "success");

    const form = document.getElementById(
      "feedback-form",
    ) as HTMLFormElement | null;
    if (form) {
      form.reset();
      const counter = document.getElementById("char-count");
      if (counter) counter.textContent = "0";
    }
  } else {
    try {
      const data = JSON.parse(xhr.responseText) as { detail?: string };
      event.detail.target.innerHTML = `
        <p class="text-sm text-red-600 bg-red-50 border border-red-200
                  rounded-lg px-4 py-3">
          ${data.detail ?? "Failed to send feedback. Please try again."}
        </p>`;
    } catch {
      event.detail.target.innerHTML = `
        <p class="text-sm text-red-600 bg-red-50 border border-red-200
                  rounded-lg px-4 py-3">
          Something went wrong. Please try again.
        </p>`;
    }
  }
}

document.addEventListener("DOMContentLoaded", initCharCount);
document.addEventListener("htmx:afterRequest", handleFeedbackResponse);
