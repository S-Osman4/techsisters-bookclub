// app/static/src/ts/pages/register.ts
import { showToast } from "../toast.js";

/**
 * Register page.
 * Handles:
 * - Password show/hide toggle (shared with login)
 * - Password match validation
 * - Submit button enable/disable
 * - Inline error display
 */

function togglePasswordVisibility(
  fieldId: string,
  btn: HTMLButtonElement,
): void {
  const input = document.getElementById(fieldId) as HTMLInputElement | null;
  const icon = document.getElementById(`eye-${fieldId}`);
  if (!input || !icon) return;

  const isHidden = input.type === "password";
  input.type = isHidden ? "text" : "password";
  btn.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");

  icon.innerHTML = isHidden
    ? `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
         d="M13.875 18.825A10.05 10.05 0 0112 19c-4.477 0-8.268-2.943-9.542-7
            a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878
            9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3
            3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.477 0 8.268 2.943 9.542
            7a10.025 10.025 0 01-4.132 4.411m0 0L21 21" />`
    : `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
         d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
         d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542
            7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />`;
}

function initPasswordValidation(): void {
  const passwordInput = document.getElementById(
    "reg-password",
  ) as HTMLInputElement | null;
  const confirmInput = document.getElementById(
    "reg-confirm",
  ) as HTMLInputElement | null;
  const matchMsg = document.getElementById("password-match-msg");
  const submitBtn = document.getElementById(
    "register-btn",
  ) as HTMLButtonElement | null;
  const form = document.getElementById(
    "register-form",
  ) as HTMLFormElement | null;

  if (!passwordInput || !confirmInput || !matchMsg || !submitBtn || !form)
    return;

  function validate(): void {
    const pw = passwordInput!.value;
    const cpw = confirmInput!.value;

    if (!cpw) {
      matchMsg!.classList.add("hidden");
      submitBtn!.disabled = pw.length < 8;
      return;
    }

    const matches = pw === cpw;
    matchMsg!.textContent = matches
      ? "Passwords match."
      : "Passwords do not match.";
    matchMsg!.className = matches
      ? "text-xs mt-1.5 text-green-600"
      : "text-xs mt-1.5 text-red-600";
    matchMsg!.classList.remove("hidden");

    confirmInput!.classList.toggle("border-green-400", matches);
    confirmInput!.classList.toggle("border-red-400", !matches);

    submitBtn!.disabled = !matches || pw.length < 8;
  }

  passwordInput.addEventListener("input", validate);
  confirmInput.addEventListener("input", validate);

  // Guard against mismatched submit
  form.addEventListener("submit", (e) => {
    if (passwordInput.value !== confirmInput.value) {
      e.preventDefault();
      showToast("Passwords do not match.", "error");
    }
  });
}

function handleRegisterError(evt: Event): void {
  const event = evt as CustomEvent<{
    target: HTMLElement;
    xhr: XMLHttpRequest;
  }>;

  if (event.detail.target.id !== "register-result") return;

  const xhr = event.detail.xhr;
  if (xhr.status < 400) return;

  const resultEl = document.getElementById("register-result");
  const submitBtn = document.getElementById(
    "register-btn",
  ) as HTMLButtonElement | null;
  if (!resultEl) return;

  try {
    const data = JSON.parse(xhr.responseText) as { detail?: string };
    resultEl.innerHTML = `
      <p class="text-sm text-red-600 bg-red-50 border border-red-200
                rounded-lg px-4 py-3">
        ${data.detail ?? "Registration failed. Please try again."}
      </p>`;
  } catch {
    resultEl.innerHTML = `
      <p class="text-sm text-red-600 bg-red-50 border border-red-200
                rounded-lg px-4 py-3">
        Something went wrong. Please try again.
      </p>`;
  }

  // Re-enable submit button after error
  if (submitBtn) submitBtn.disabled = false;
}

// Expose to HTML onclick attributes
(window as unknown as Record<string, unknown>)["togglePasswordVisibility"] =
  togglePasswordVisibility;

document.addEventListener("DOMContentLoaded", initPasswordValidation);
document.addEventListener("htmx:afterRequest", handleRegisterError);
