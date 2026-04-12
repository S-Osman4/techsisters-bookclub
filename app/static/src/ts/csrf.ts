// app/static/src/ts/csrf.ts

/**
 * Read the CSRF token from the csrftoken cookie.
 * Returns empty string if not found.
 */
export function getCsrfToken(): string {
  const match = document.cookie
    .split(";")
    .map((c) => c.trim())
    .find((c) => c.startsWith("csrftoken="));

  return match ? (match.split("=")[1] ?? "") : "";
}

/**
 * Inject the CSRF token into every HTMX request as the
 * X-CSRFToken header. Called once on DOMContentLoaded.
 */
export function initCsrf(): void {
  document.addEventListener("htmx:configRequest", (evt: Event) => {
    const event = evt as CustomEvent<{ headers: Record<string, string> }>;
    event.detail.headers["X-CSRFToken"] = getCsrfToken();
  });
}
