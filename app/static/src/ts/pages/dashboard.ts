// app/static/src/ts/pages/dashboard.ts
import { showToast } from "../toast.js";

/**
 * Dashboard page.
 *
 * Handles:
 * - Tab switching (upcoming / past) with URL state
 * - Progress update response
 * - Suggestion form response + reset
 * - Scroll to section from URL hash on load
 */

// ── Tab switching ─────────────────────────────────────────────────────────────

type TabName = "upcoming" | "past";

function switchTab(name: TabName): void {
  const tabs = ["upcoming", "past"] as const;
  const panels = { upcoming: "panel-upcoming", past: "panel-past" };
  const tabEls = { upcoming: "tab-upcoming", past: "tab-past" };

  tabs.forEach((t) => {
    const tab = document.getElementById(tabEls[t]);
    const panel = document.getElementById(panels[t]);
    if (!tab || !panel) return;

    const isActive = t === name;
    panel.classList.toggle("hidden", !isActive);
    tab.setAttribute("aria-selected", String(isActive));

    if (isActive) {
      tab.classList.add("border-primary", "text-primary");
      tab.classList.remove("border-transparent", "text-gray-500");
    } else {
      tab.classList.remove("border-primary", "text-primary");
      tab.classList.add("border-transparent", "text-gray-500");
    }
  });

  // Sync to URL without reload
  const url = new URL(window.location.href);
  url.searchParams.set("tab", name);
  window.history.replaceState({}, "", url.toString());
}

// ── Progress update response ──────────────────────────────────────────────────

function handleProgressResponse(evt: Event): void {
  const event = evt as CustomEvent<{
    target: HTMLElement;
    xhr: XMLHttpRequest;
  }>;

  if (event.detail.target.id !== "progress-result") return;
  const xhr = event.detail.xhr;

  if (xhr.status >= 200 && xhr.status < 300) {
    try {
      const data = JSON.parse(xhr.responseText) as { message?: string };
      if (data.message) {
        showToast(data.message, "success");
        event.detail.target.innerHTML = "";
        document.body.dispatchEvent(new Event("progress-updated"));
      }
    } catch {
      // Non-JSON
    }
  } else {
    try {
      const data = JSON.parse(xhr.responseText) as { detail?: string };
      event.detail.target.innerHTML = `
        <p class="text-sm text-red-600 mt-1">
          ${data.detail ?? "Failed to update progress."}
        </p>`;
    } catch {
      event.detail.target.innerHTML = `
        <p class="text-sm text-red-600 mt-1">
          Something went wrong. Please try again.
        </p>`;
    }
  }
}

// ── Suggestion form response ──────────────────────────────────────────────────

function handleSuggestionResponse(evt: Event): void {
  const event = evt as CustomEvent<{
    target: HTMLElement;
    xhr: XMLHttpRequest;
    elt: HTMLElement;
  }>;

  if (event.detail.target.id !== "suggestion-result") return;
  const xhr = event.detail.xhr;

  if (xhr.status >= 200 && xhr.status < 300) {
    try {
      const data = JSON.parse(xhr.responseText) as { message?: string };
      if (data.message) {
        showToast(data.message, "success");
        event.detail.target.innerHTML = "";

        // Reset the suggestion form
        const form = document.getElementById(
          "suggestion-form",
        ) as HTMLFormElement | null;
        form?.reset();

        // Reload to show the new suggestion in the list
        setTimeout(() => window.location.reload(), 1200);
      }
    } catch {
      // Non-JSON
    }
  } else {
    try {
      const data = JSON.parse(xhr.responseText) as { detail?: string };
      event.detail.target.innerHTML = `
        <p class="text-sm text-red-600 bg-red-50 border border-red-200
                  rounded-lg px-4 py-3">
          ${data.detail ?? "Failed to submit suggestion."}
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

// ── Initialise ────────────────────────────────────────────────────────────────

function init(): void {
  // Restore tab from URL
  const params = new URLSearchParams(window.location.search);
  const tab = params.get("tab");
  if (tab === "past" || tab === "upcoming") {
    switchTab(tab);
  }

  // Scroll to hash section (e.g. #suggest-book from nav redirect)
  const hash = window.location.hash;
  if (hash) {
    const el = document.querySelector(hash);
    if (el) {
      setTimeout(() => {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    }
  }
}

// Expose tab switch for inline onclick in template
(window as unknown as Record<string, unknown>)["switchTab"] = switchTab;

document.addEventListener("DOMContentLoaded", init);
document.addEventListener("htmx:afterRequest", handleProgressResponse);
document.addEventListener("htmx:afterRequest", handleSuggestionResponse);
