// app/static/src/ts/pages/profile.ts
import { showToast } from "../toast.js";

/**
 * Profile page.
 *
 * Handles:
 * - Password show/hide toggle (shared pattern)
 * - Name update response (updates displayed name without reload)
 * - Password change response (clears session → redirect)
 * - Account deletion response (redirect to home)
 */

// ── Password toggle ───────────────────────────────────────────────────────────

function togglePasswordVisibility(
  fieldId: string,
  btn: HTMLButtonElement
): void {
  const input = document.getElementById(fieldId) as HTMLInputElement | null;
  const icon  = document.getElementById(`eye-${fieldId}`);
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

// ── HTMX response handlers ────────────────────────────────────────────────────

function handleProfileResponse(evt: Event): void {
  const event = evt as CustomEvent<{
    target: HTMLElement;
    xhr: XMLHttpRequest;
  }>;

  const { target, xhr } = event.detail;
  const targetId = target.id;

  if (!["name-result", "password-result", "delete-result"]
    .includes(targetId)) return;

  if (xhr.status >= 200 && xhr.status < 300) {
    try {
      const data = JSON.parse(xhr.responseText) as {
        message?: string;
        success?: boolean;
      };

      if (!data.success && !data.message) return;

      if (targetId === "name-result") {
        showToast(data.message ?? "Name updated.", "success");
        target.innerHTML = "";

        // Update displayed name without reload
        const nameDisplay = document.getElementById("profile-name-display");
        const nameInput   = document.getElementById("new-name") as
          HTMLInputElement | null;
        if (nameDisplay && nameInput) {
          nameDisplay.textContent = nameInput.value;
        }

        // Update avatar initial
        const avatar = document.querySelector<HTMLElement>(
          "[data-avatar-initial]"
        );
        if (avatar && nameInput?.value) {
          avatar.textContent = nameInput.value[0].toUpperCase();
        }
      }

      if (targetId === "password-result") {
        showToast(
          data.message ?? "Password changed. Redirecting...",
          "success"
        );
        setTimeout(() => { window.location.href = "/login"; }, 1500);
      }

      if (targetId === "delete-result") {
        showToast(data.message ?? "Account deleted.", "success");
        setTimeout(() => { window.location.href = "/"; }, 1800);
      }
    } catch {
      // Non-JSON response
    }
  } else {
    try {
      const data = JSON.parse(xhr.responseText) as { detail?: string };
      target.innerHTML = `
        <p class="text-sm text-red-600 bg-red-50 border border-red-200
                  rounded-lg px-4 py-3 mt-2">
          ${data.detail ?? "Something went wrong. Please try again."}
        </p>`;
    } catch {
      target.innerHTML = `
        <p class="text-sm text-red-600 bg-red-50 border border-red-200
                  rounded-lg px-4 py-3 mt-2">
          Something went wrong. Please try again.
        </p>`;
    }
  }
}

// ── Expose to HTML onclick ────────────────────────────────────────────────────

(window as unknown as Record<string, unknown>)
  ["togglePasswordVisibility"] = togglePasswordVisibility;

document.addEventListener("htmx:afterRequest", handleProfileResponse);