// app/static/src/ts/pages/past-books.ts

/**
 * Past books and upcoming books pages.
 * Both pages use this same script.
 *
 * Handles:
 * - Clear search button
 * - Restore search input from URL on load
 * - Re-init Lucide icons after HTMX grid swap
 */

function clearSearch(): void {
  const input = document.getElementById(
    "search-input",
  ) as HTMLInputElement | null;
  if (!input) return;

  input.value = "";

  // Trigger HTMX to reload the grid without the search param
  if (window.htmx) {
    window.htmx.trigger(input, "search");
  }

  // Clean the URL
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

// Expose clear function to HTML onclick
(window as unknown as Record<string, unknown>)["clearSearch"] = clearSearch;

document.addEventListener("DOMContentLoaded", restoreSearchFromUrl);
