/**
 * Past books and upcoming books pages.
 *
 * Handles:
 * - Clear search
 * - Restore search from URL
 * - Enter key → trigger search button (single request, shows spinner)
 */

function clearSearch(): void {
  const input = document.getElementById(
    "search-input",
  ) as HTMLInputElement | null;
  if (!input) return;

  input.value = "";
  // Trigger HTMX search via button (shows spinner)
  const button = document.getElementById(
    "search-btn",
  ) as HTMLButtonElement | null;
  if (button) button.click();

  // Clean URL
  const url = new URL(window.location.href);
  url.searchParams.delete("search");
  window.history.replaceState({}, "", url.toString());
}

function restoreSearchFromUrl(): void {
  const params = new URLSearchParams(window.location.search);
  const search = params.get("search");
  const input = document.getElementById(
    "search-input",
  ) as HTMLInputElement | null;
  if (input && search) {
    input.value = search;
  }
}

function handleEnterKey(): void {
  const input = document.getElementById(
    "search-input",
  ) as HTMLInputElement | null;
  const button = document.getElementById(
    "search-btn",
  ) as HTMLButtonElement | null;
  if (!input || !button) return;

  input.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault(); // Block input's "search" event
      button.click(); // ✅ Triggers button HTMX + spinner
    }
  });
}

// Expose to HTML
(window as unknown as Record<string, unknown>)["clearSearch"] = clearSearch;

document.addEventListener("DOMContentLoaded", () => {
  restoreSearchFromUrl();
  handleEnterKey();
});
