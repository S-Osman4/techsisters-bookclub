// app/static/src/ts/url-errors.ts
import { showToast } from "./toast.js";
import type { ToastType } from "./types.js";

const ERROR_MESSAGES: Record<string, [string, ToastType]> = {
  access_required: ["Please enter the access code first.", "warning"],
  verify_code_first: [
    "Please verify the access code before registering.",
    "warning",
  ],
  login_required: ["Please log in to continue.", "error"],
  access_denied: ["You don't have permission to do that.", "error"],
  page_not_found: ["Page not found.", "error"],
  validation_error: ["Please check your input and try again.", "warning"],
  server_error: ["An unexpected error occurred. Please try again.", "error"],
  auth_required: ["Authentication required. Please log in.", "error"],
  invalid_credentials: ["Invalid email or password.", "error"],
};

/**
 * On page load, check for ?error= query param,
 * show the corresponding toast, then clean the URL.
 */
export function initUrlErrors(): void {
  const params = new URLSearchParams(window.location.search);
  const error = params.get("error");

  if (!error) return;

  const [message, type] = ERROR_MESSAGES[error] ?? [
    "Something went wrong.",
    "error" as ToastType,
  ];

  showToast(message, type);

  // Remove ?error= from URL without reload
  const clean = window.location.pathname;
  window.history.replaceState({}, document.title, clean);
}
