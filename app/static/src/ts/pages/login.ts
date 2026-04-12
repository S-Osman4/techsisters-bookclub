// app/static/src/ts/pages/login.ts

/**
 * Login page.
 * Handles:
 * - Password show/hide toggle
 * - Inline error display on failed login
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

function handleLoginError(evt: Event): void {
  const event = evt as CustomEvent<{
    target: HTMLElement;
    xhr: XMLHttpRequest;
  }>;

  if (event.detail.target.id !== "login-result") return;

  const xhr = event.detail.xhr;
  if (xhr.status < 400) return;

  const resultEl = document.getElementById("login-result");
  if (!resultEl) return;

  try {
    const data = JSON.parse(xhr.responseText) as { detail?: string };
    resultEl.innerHTML = `
      <p class="text-sm text-red-600 bg-red-50 border border-red-200
                rounded-lg px-4 py-3">
        ${data.detail ?? "Login failed. Please try again."}
      </p>`;
  } catch {
    resultEl.innerHTML = `
      <p class="text-sm text-red-600 bg-red-50 border border-red-200
                rounded-lg px-4 py-3">
        Something went wrong. Please try again.
      </p>`;
  }
}

// Expose toggle to HTML onclick attributes
(window as unknown as Record<string, unknown>)["togglePasswordVisibility"] =
  togglePasswordVisibility;

document.addEventListener("htmx:afterRequest", handleLoginError);
