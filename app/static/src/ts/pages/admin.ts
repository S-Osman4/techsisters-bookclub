// app/static/src/ts/pages/admin.ts
import { showToast } from "../toast.js";
import { openModal, closeModal } from "../modal.js";
import "../admin_guide.js";

/**
 * Admin page — all interactive admin panel operations.
 *
 * Pattern for every action:
 * 1. Open modal with relevant data
 * 2. User confirms
 * 3. fetch() to API
 * 4. Show toast + reload or show inline error
 */

// ── State ─────────────────────────────────────────────────────────────────────

interface SuggestionState {
  id: string;
  title: string;
  cover: string;
  pdf: string;
  user: string;
  action: "approve" | "reject";
}

interface UserState {
  id: string;
  name: string;
}

let currentSuggestion: SuggestionState | null = null;
let currentUser: UserState | null = null;

// ── Helpers ───────────────────────────────────────────────────────────────────

function getAdminData(): {
  currentBookId: string;
  adminCount: number;
} {
  const el = document.getElementById("admin-data");
  return {
    currentBookId: el?.dataset.currentBookId ?? "",
    adminCount: parseInt(el?.dataset.adminCount ?? "0", 10),
  };
}

function setButtonLoading(
  btnId: string,
  loading: boolean,
  loadingText = "Saving...",
): void {
  const btn = document.getElementById(btnId) as HTMLButtonElement | null;
  if (!btn) return;

  const text = btn.querySelector<HTMLElement>(".btn-text");
  const spinner = btn.querySelector<HTMLElement>(".loading-spinner");

  btn.disabled = loading;
  if (text) text.style.display = loading ? "none" : "";
  if (spinner) spinner.style.display = loading ? "inline-flex" : "none";
  if (loading && spinner) spinner.textContent = loadingText;
}

function showResult(elId: string, message: string, isError = false): void {
  const el = document.getElementById(elId);
  if (!el) return;
  el.innerHTML = `
    <p class="text-sm ${
      isError
        ? "text-red-600 bg-red-50 border border-red-200"
        : "text-green-700 bg-green-50 border border-green-200"
    }
      rounded-lg px-4 py-3 mt-1">
      ${message}
    </p>`;
}

function reloadAfter(ms = 1200): void {
  setTimeout(() => window.location.reload(), ms);
}

/**
 * Refresh both suggestion-related partials in-place without a full page reload.
 * All errors are handled internally — this function never throws.
 * Also updates the stat badge in the header.
 */
function refreshSuggestionPartials(): void {
  const pendingTarget = document.getElementById(
    "pending-suggestions-container",
  );
  const queueTarget = document.getElementById("approved-queue-container");

  if (!pendingTarget || !queueTarget) {
    window.location.reload();
    return;
  }

  Promise.all([
    fetch("/api/admin/partials/pending-suggestions").then((r) => {
      if (!r.ok) throw new Error(`partial pending ${r.status}`);
      return r.text();
    }),
    fetch("/api/admin/partials/approved-queue").then((r) => {
      if (!r.ok) throw new Error(`partial queue ${r.status}`);
      return r.text();
    }),
  ])
    .then(([pendingHtml, queueHtml]) => {
      pendingTarget.innerHTML = pendingHtml;
      queueTarget.innerHTML = queueHtml;
      attachSuggestionButtons();
      attachSetCurrentButtons();
      // Update the pending count stat badge
      const badge = document.getElementById("stat-pending-count");
      const items = pendingTarget.querySelectorAll("[data-id]");
      if (badge) badge.textContent = String(items.length);
    })
    .catch(() => {
      window.location.reload();
    });
}

// ── Chapter assignment helpers ─────────────────────────────────────────────────
// prefix: "set-current" | "edit-book"
// IDs:    set-current-chapter-from / set-current-chapter-to
//         edit-chapter-from        / edit-chapter-to

type ChapterPrefix = "set-current" | "edit-book";

function _chapterIds(prefix: ChapterPrefix): {
  fromId: string;
  toId: string;
  previewId: string;
} {
  return {
    fromId:
      prefix === "set-current"
        ? "set-current-chapter-from"
        : "edit-chapter-from",
    toId:
      prefix === "set-current" ? "set-current-chapter-to" : "edit-chapter-to",
    previewId:
      prefix === "set-current" ? "sc-chapter-preview" : "eb-chapter-preview",
  };
}

/**
 * When the admin types in "From", auto-fill "To" with the same value
 * only if "To" hasn't been manually changed yet (i.e. it's empty or equals old From).
 * Then update the preview.
 */
function chapterAutoFill(prefix: ChapterPrefix): void {
  const { fromId, toId } = _chapterIds(prefix);
  const fromEl = document.getElementById(fromId) as HTMLInputElement | null;
  const toEl = document.getElementById(toId) as HTMLInputElement | null;
  if (!fromEl || !toEl) return;

  // Auto-fill "To" only when it's empty or currently matches "From" (user hasn't customised it)
  if (toEl.value === "" || toEl.value === fromEl.dataset.lastFrom) {
    toEl.value = fromEl.value;
  }
  fromEl.dataset.lastFrom = fromEl.value;
  chapterPreview(prefix);
}

/** Update the live preview line under the chapter fields. */
function chapterPreview(prefix: ChapterPrefix): void {
  const { fromId, toId, previewId } = _chapterIds(prefix);
  const fromVal = (document.getElementById(fromId) as HTMLInputElement | null)
    ?.value;
  const toVal = (document.getElementById(toId) as HTMLInputElement | null)
    ?.value;
  const preview = document.getElementById(previewId);
  if (!preview) return;

  const from = fromVal ? parseInt(fromVal, 10) : null;
  const to = toVal ? parseInt(toVal, 10) : null;

  if (from === null) {
    preview.textContent = "";
    return;
  }

  if (to !== null && to < from) {
    preview.textContent = "⚠ 'To' must be ≥ 'From'";
    preview.className = "text-xs font-medium mt-1.5 min-h-[1rem] text-red-500";
    return;
  }

  const label =
    to === null || from === to ? `Chapter ${from}` : `Chapters ${from}–${to}`;

  preview.textContent = `Members will see: "${label}"`;
  preview.className = "text-xs font-medium mt-1.5 min-h-[1rem] text-secondary";
}

/** Read the final chapter_from / chapter_to values from a modal. */
function getChapterValues(prefix: ChapterPrefix): {
  from: number | null;
  to: number | null;
} {
  const { fromId, toId } = _chapterIds(prefix);
  const fVal = (document.getElementById(fromId) as HTMLInputElement | null)
    ?.value;
  const tVal = (document.getElementById(toId) as HTMLInputElement | null)
    ?.value;
  const from = fVal ? parseInt(fVal, 10) : null;
  const to = tVal ? parseInt(tVal, 10) : from; // default to same as from
  return { from, to };
}

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Typed API response shape.
 * FastAPI returns { message, success } on success, { detail } on error.
 */
interface ApiResponse {
  success?: boolean;
  message?: string;
  detail?: string;
  [key: string]: unknown;
}

/**
 * Fetch wrapper that always resolves to a structured object.
 * Non-2xx responses are parsed and returned with success=false.
 * Network failures throw so callers can catch them.
 */
async function apiFetch(
  url: string,
  method: string,
  body: unknown,
): Promise<ApiResponse> {
  const token = getCsrfToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["X-CSRFToken"] = token;
  }

  const res = await fetch(url, {
    method,
    headers,
    body: JSON.stringify(body),
  });

  let data: ApiResponse;
  try {
    data = await res.json();
  } catch {
    // Response body wasn't valid JSON (e.g. empty 204)
    data = {};
  }

  if (!res.ok) {
    // Normalise error shape: FastAPI uses { detail }, we want success=false
    return {
      success: false,
      detail: data.detail ?? `HTTP ${res.status}`,
      ...data,
    };
  }

  // FastAPI success responses include { message, success: true }
  return { success: true, ...data };
}

// ── Access code ───────────────────────────────────────────────────────────────

let _generatedCode = "";

async function generateCode(): Promise<void> {
  setButtonLoading("generate-btn", true, "Generating...");
  try {
    const data = await apiFetch("/api/admin/code/generate", "POST", {});
    _generatedCode = (data as { generated_code?: string }).generated_code ?? "";
    const input = document.getElementById(
      "new-code-input",
    ) as HTMLInputElement | null;
    if (input) input.value = _generatedCode;
    showResult(
      "code-modal-result",
      `Generated: <strong>${_generatedCode}</strong>. Click Update to save.`,
    );
  } catch {
    showResult("code-modal-result", "Failed to generate code.", true);
  } finally {
    setButtonLoading("generate-btn", false);
    const btn = document.getElementById("generate-btn");
    if (btn)
      (btn.querySelector(".btn-text") as HTMLElement).textContent = "Generate";
  }
}

async function updateAccessCode(): Promise<void> {
  const input = document.getElementById(
    "new-code-input",
  ) as HTMLInputElement | null;
  const code = input?.value.trim().toUpperCase() ?? "";

  if (!code || code.length < 4) {
    showResult(
      "code-modal-result",
      "Code must be at least 4 characters.",
      true,
    );
    return;
  }

  setButtonLoading("update-code-btn", true, "Updating...");
  try {
    const data = await apiFetch("/api/admin/code", "PUT", { new_code: code });
    if (data.success) {
      showToast(data.message ?? "Access code updated.", "success");
      closeModal("admin-code-modal");
      reloadAfter();
    } else {
      showResult(
        "code-modal-result",
        data.detail ?? "Failed to update code.",
        true,
      );
    }
  } catch {
    showResult("code-modal-result", "Network error. Please try again.", true);
  } finally {
    setButtonLoading("update-code-btn", false);
  }
}

// Access code reveal / copy
let codeRevealed = false;
const REAL_CODE = document.getElementById("admin-data")?.dataset.realCode ?? "";

function toggleCodeReveal(): void {
  const display = document.getElementById("code-display");
  const btn = document.getElementById("code-reveal-btn");
  if (!display || !btn) return;

  codeRevealed = !codeRevealed;
  display.textContent = codeRevealed ? REAL_CODE || "••••••••" : "••••••••";
  btn.textContent = codeRevealed ? "Hide" : "Reveal";
  btn.setAttribute("aria-pressed", String(codeRevealed));
}

async function copyAccessCode(): Promise<void> {
  if (!REAL_CODE) return;
  try {
    await navigator.clipboard.writeText(REAL_CODE);
    showToast("Access code copied to clipboard.", "success", 2000);
  } catch {
    showToast("Could not copy. Please reveal and copy manually.", "warning");
  }
}

// ── Current book ──────────────────────────────────────────────────────────────

async function updateCurrentBook(): Promise<void> {
  const title = (
    document.getElementById("edit-title") as HTMLInputElement
  )?.value.trim();
  const pdf = (
    document.getElementById("edit-pdf") as HTMLInputElement
  )?.value.trim();
  const cover = (
    document.getElementById("edit-cover") as HTMLInputElement
  )?.value.trim();
  const total = (
    document.getElementById("edit-total") as HTMLInputElement
  )?.value.trim();
  const { from: chapterFrom, to: chapterTo } = getChapterValues("edit-book");

  if (!title) {
    showResult("edit-book-result", "Title is required.", true);
    return;
  }
  if (chapterFrom !== null && chapterTo !== null && chapterTo < chapterFrom) {
    showResult(
      "edit-book-result",
      "'To chapter' must be ≥ 'From chapter'.",
      true,
    );
    return;
  }

  setButtonLoading("edit-book-btn", true, "Saving...");
  try {
    const data = await apiFetch("/api/admin/books/current", "PUT", {
      title: title || undefined,
      pdf_url: pdf || undefined,
      cover_image_url: cover || undefined,
      chapter_from: chapterFrom ?? undefined,
      chapter_to: chapterTo ?? undefined,
      total_chapters: total ? parseInt(total, 10) : undefined,
    });
    if (data.success) {
      showToast(data.message ?? "Book updated.", "success");
      closeModal("admin-edit-book-modal");
      reloadAfter();
    } else {
      showResult(
        "edit-book-result",
        data.detail ?? "Failed to update book.",
        true,
      );
    }
  } catch {
    showResult("edit-book-result", "Network error.", true);
  } finally {
    setButtonLoading("edit-book-btn", false);
  }
}

async function completeCurrentBook(): Promise<void> {
  setButtonLoading("complete-book-btn", true, "Completing...");
  try {
    const data = await apiFetch("/api/admin/books/complete", "POST", {});
    if (data.success) {
      showToast(data.message ?? "Book marked as completed.", "success");
      closeModal("admin-complete-book-modal");
      reloadAfter();
    } else {
      showResult(
        "complete-result",
        data.detail ?? "Failed to complete book.",
        true,
      );
    }
  } catch {
    showResult("complete-result", "Network error.", true);
  } finally {
    setButtonLoading("complete-book-btn", false);
  }
}

// ── Meeting ───────────────────────────────────────────────────────────────────

function toggleCancellationNote(show: boolean): void {
  const section = document.getElementById("cancellation-note-section");
  if (section) section.classList.toggle("hidden", !show);
}

async function saveMeeting(): Promise<void> {
  const dt = (document.getElementById("meeting-datetime") as HTMLInputElement)
    ?.value;
  const link = (
    document.getElementById("meeting-link") as HTMLInputElement
  )?.value.trim();
  const cancelled =
    (document.getElementById("meeting-cancelled") as HTMLInputElement)
      ?.checked ?? false;
  const note = (
    document.getElementById("cancellation-note") as HTMLInputElement
  )?.value.trim();

  if (!dt || !link) {
    showResult("meeting-result", "Date, time, and link are required.", true);
    return;
  }

  setButtonLoading("meeting-save-btn", true, "Saving...");
  try {
    const data = await apiFetch("/api/admin/meeting", "PUT", {
      start_at_local: dt,
      timezone: "Europe/London",
      meet_link: link,
      is_cancelled: cancelled,
      cancellation_note: cancelled ? note || null : null,
    });
    if (data.success) {
      showToast(data.message ?? "Meeting updated.", "success");
      closeModal("admin-meeting-modal");
      reloadAfter();
    } else {
      showResult(
        "meeting-result",
        data.detail ?? "Failed to update meeting.",
        true,
      );
    }
  } catch {
    showResult("meeting-result", "Network error.", true);
  } finally {
    setButtonLoading("meeting-save-btn", false);
  }
}

// ── Suggestions ───────────────────────────────────────────────────────────────

function openSuggestionModal(
  btn: HTMLElement,
  action: "approve" | "reject",
): void {
  const id = btn.dataset.id ?? "";
  const title = btn.dataset.title ?? "";
  const cover = btn.dataset.cover ?? "";
  const pdf = btn.dataset.pdf ?? "";
  const user = btn.dataset.user ?? "";

  currentSuggestion = { id, title, cover, pdf, user, action };

  // Populate modal
  const titleEl = document.getElementById("suggestion-modal-title-text");
  const userEl = document.getElementById("suggestion-modal-user");
  const pdfEl = document.getElementById(
    "suggestion-modal-pdf",
  ) as HTMLAnchorElement | null;
  const coverEl = document.getElementById("suggestion-modal-cover");
  const confirmText = document.getElementById("suggestion-confirm-text");
  const confirmBtn = document.getElementById("suggestion-confirm-btn");
  const coverSection = document.getElementById("cover-input-section");
  const resultEl = document.getElementById("suggestion-modal-result");

  if (titleEl) titleEl.textContent = title;
  if (userEl) userEl.textContent = `Suggested by ${user}`;
  if (pdfEl) pdfEl.href = pdf;
  if (resultEl) resultEl.innerHTML = "";

  // Cover preview
  if (coverEl) {
    if (cover) {
      coverEl.innerHTML = `<img src="${cover}" alt="${title}"
        class="w-full h-full object-contain" loading="lazy" />`;
    } else {
      coverEl.innerHTML = `<svg class="w-6 h-6 text-gray-400"
        fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round"
              stroke-width="1.5"
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168
                 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477
                 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0
                 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5
                 18c-1.746 0-3.332.477-4.5 1.253" /></svg>`;
    }
  }

  // Pre-fill cover URL input
  const coverInput = document.getElementById(
    "suggestion-cover-url",
  ) as HTMLInputElement | null;
  if (coverInput) coverInput.value = cover;

  // Configure for action
  if (action === "approve") {
    if (confirmText) confirmText.textContent = "Approve and add to queue";
    if (confirmBtn) confirmBtn.className = "btn btn-secondary flex-1";
    if (coverSection) coverSection.classList.remove("hidden");
  } else {
    if (confirmText) confirmText.textContent = "Reject suggestion";
    if (confirmBtn) confirmBtn.className = "btn btn-danger flex-1";
    if (coverSection) coverSection.classList.add("hidden");
  }

  openModal("admin-suggestion-modal");
}

async function confirmSuggestionAction(): Promise<void> {
  if (!currentSuggestion) return;
  const { id, action } = currentSuggestion;

  if (action === "approve") {
    const coverUrl =
      (
        document.getElementById(
          "suggestion-cover-url",
        ) as HTMLInputElement | null
      )?.value.trim() ?? "";

    if (!coverUrl) {
      showResult(
        "suggestion-modal-result",
        "A cover image URL is required to approve a book.",
        true,
      );
      return;
    }

    setButtonLoading("suggestion-confirm-btn", true, "Approving...");
    try {
      const data = await apiFetch(
        `/api/admin/suggestions/${id}/approve`,
        "PUT",
        { cover_image_url: coverUrl },
      );

      if (data.success) {
        showToast(data.message ?? "Suggestion approved.", "success");
        closeModal("admin-suggestion-modal");
        refreshSuggestionPartials();
      } else {
        // 409 "already approved" means it went through on a previous attempt —
        // treat it as success so the UI reflects the real server state.
        const detail = (data.detail ?? "").toLowerCase();
        if (detail.includes("already")) {
          showToast("Suggestion was already approved — refreshing.", "success");
          closeModal("admin-suggestion-modal");
          refreshSuggestionPartials();
        } else {
          showResult(
            "suggestion-modal-result",
            data.detail ?? "Failed to approve.",
            true,
          );
        }
      }
    } catch {
      showResult(
        "suggestion-modal-result",
        "Network error. Please try again.",
        true,
      );
    } finally {
      setButtonLoading("suggestion-confirm-btn", false);
    }
  } else {
    setButtonLoading("suggestion-confirm-btn", true, "Rejecting...");
    try {
      const data = await apiFetch(
        `/api/admin/suggestions/${id}/reject`,
        "PUT",
        {},
      );

      if (data.success) {
        showToast(data.message ?? "Suggestion rejected.", "success");
        closeModal("admin-suggestion-modal");
        refreshSuggestionPartials();
      } else {
        const detail = (data.detail ?? "").toLowerCase();
        if (detail.includes("already")) {
          showToast("Suggestion was already actioned — refreshing.", "success");
          closeModal("admin-suggestion-modal");
          refreshSuggestionPartials();
        } else {
          showResult(
            "suggestion-modal-result",
            data.detail ?? "Failed to reject.",
            true,
          );
        }
      }
    } catch {
      showResult(
        "suggestion-modal-result",
        "Network error. Please try again.",
        true,
      );
    } finally {
      setButtonLoading("suggestion-confirm-btn", false);
    }
  }
}

// ── Set current book ──────────────────────────────────────────────────────────

// Named handler functions for event listeners (so they can be removed if needed)
function handleSetCurrentFromInput(this: HTMLInputElement) {
  chapterAutoFill("set-current");
}
function handleSetCurrentToInput(this: HTMLInputElement) {
  chapterPreview("set-current");
}
function handleEditFromInput(this: HTMLInputElement) {
  chapterAutoFill("edit-book");
}
function handleEditToInput(this: HTMLInputElement) {
  chapterPreview("edit-book");
}

let pendingBookId = "";

function openSetCurrentModal(btn: HTMLElement): void {
  console.log("📂 openSetCurrentModal, pendingBookId:", btn.dataset.id);
  pendingBookId = btn.dataset.id ?? "";
  const title = btn.dataset.title ?? "";
  const cover = btn.dataset.cover ?? "";

  const titleEl = document.getElementById("set-current-book-title");
  const coverEl = document.getElementById(
    "set-current-cover",
  ) as HTMLInputElement | null;
  const resultEl = document.getElementById("set-current-result");
  const preview = document.getElementById("sc-chapter-preview");
  const fromEl = document.getElementById(
    "set-current-chapter-from",
  ) as HTMLInputElement | null;
  const toEl = document.getElementById(
    "set-current-chapter-to",
  ) as HTMLInputElement | null;
  const totalEl = document.getElementById(
    "set-current-total",
  ) as HTMLInputElement | null;

  if (titleEl) titleEl.textContent = `Setting "${title}" as the current book.`;
  if (coverEl) coverEl.value = cover;
  if (resultEl) resultEl.innerHTML = "";
  if (preview) preview.textContent = "";
  if (fromEl) {
    fromEl.value = "";
    delete fromEl.dataset.lastFrom;
  }
  if (toEl) toEl.value = "";
  if (totalEl) totalEl.value = "";

  // No need to attach listeners here — they are already attached in init()
  openModal("admin-set-current-modal");
}

async function setCurrentBook(): Promise<void> {
  console.log("🔥 setCurrentBook called");

  const { from: chapterFrom, to: chapterTo } = getChapterValues("set-current");
  const cover =
    (
      document.getElementById("set-current-cover") as HTMLInputElement | null
    )?.value.trim() ?? "";
  const total =
    (
      document.getElementById("set-current-total") as HTMLInputElement | null
    )?.value.trim() ?? "";

  if (chapterFrom === null) {
    showResult("set-current-result", "Chapter is required.", true);
    return;
  }
  if (chapterTo !== null && chapterTo < chapterFrom) {
    showResult(
      "set-current-result",
      "'To chapter' must be ≥ 'From chapter'.",
      true,
    );
    return;
  }

  // Log what we're about to send
  console.log("setCurrentBook payload:", {
    chapter_from: chapterFrom,
    chapter_to: chapterTo ?? chapterFrom,
    cover_image_url: cover || undefined,
    total_chapters: total ? parseInt(total, 10) : undefined,
  });

  setButtonLoading("set-current-btn", true, "Setting...");
  try {
    const data = await apiFetch(
      `/api/admin/books/${pendingBookId}/set-current`,
      "POST",
      {
        chapter_from: chapterFrom,
        chapter_to: chapterTo ?? chapterFrom,
        cover_image_url: cover || undefined,
        total_chapters: total ? parseInt(total, 10) : undefined,
      },
    );
    if (data.success) {
      showToast(data.message ?? "Current book set.", "success");
      closeModal("admin-set-current-modal");
      reloadAfter();
    } else {
      showResult(
        "set-current-result",
        data.detail ?? "Failed to set current book.",
        true,
      );
    }
  } catch {
    showResult("set-current-result", "Network error.", true);
  } finally {
    setButtonLoading("set-current-btn", false);
  }
}

// ── User management ───────────────────────────────────────────────────────────

function openUserModal(btn: HTMLElement, action: "promote" | "demote"): void {
  const { adminCount } = getAdminData();
  if (action === "demote" && adminCount <= 1) {
    showToast("Cannot demote the last admin.", "warning");
    return;
  }

  currentUser = {
    id: btn.dataset.id ?? "",
    name: btn.dataset.name ?? "",
  };

  const modalId =
    action === "promote" ? "admin-promote-modal" : "admin-demote-modal";
  const nameElId =
    action === "promote" ? "promote-user-name" : "demote-user-name";
  const resultId = action === "promote" ? "promote-result" : "demote-result";

  const nameEl = document.getElementById(nameElId);
  const resultEl = document.getElementById(resultId);

  if (nameEl) nameEl.textContent = currentUser.name;
  if (resultEl) resultEl.innerHTML = "";

  openModal(modalId);
}

async function confirmUserAction(action: "promote" | "demote"): Promise<void> {
  if (!currentUser) return;

  const btnId =
    action === "promote" ? "promote-confirm-btn" : "demote-confirm-btn";
  const resultId = action === "promote" ? "promote-result" : "demote-result";
  const modalId =
    action === "promote" ? "admin-promote-modal" : "admin-demote-modal";
  const endpoint = `/api/admin/users/${currentUser.id}/${action}`;

  setButtonLoading(
    btnId,
    true,
    action === "promote" ? "Promoting..." : "Demoting...",
  );
  try {
    const data = await apiFetch(endpoint, "PUT", {});
    if (data.success) {
      showToast(data.message ?? `User ${action}d.`, "success");
      closeModal(modalId);
      reloadAfter();
    } else {
      showResult(resultId, data.detail ?? `Failed to ${action}.`, true);
    }
  } catch {
    showResult(resultId, "Network error.", true);
  } finally {
    setButtonLoading(btnId, false);
  }
}

// ── Event listener attachment (extracted so it can run after partial refresh) ──

function attachSuggestionButtons(): void {
  document.querySelectorAll<HTMLElement>(".approve-btn").forEach((btn) => {
    // Clone to remove any previously attached listeners before re-attaching
    const fresh = btn.cloneNode(true) as HTMLElement;
    btn.replaceWith(fresh);
    fresh.addEventListener("click", () =>
      openSuggestionModal(fresh, "approve"),
    );
  });
  document.querySelectorAll<HTMLElement>(".reject-btn").forEach((btn) => {
    const fresh = btn.cloneNode(true) as HTMLElement;
    btn.replaceWith(fresh);
    fresh.addEventListener("click", () => openSuggestionModal(fresh, "reject"));
  });
}

function attachSetCurrentButtons(): void {
  document.querySelectorAll<HTMLElement>(".set-current-btn").forEach((btn) => {
    const fresh = btn.cloneNode(true) as HTMLElement;
    btn.replaceWith(fresh);
    fresh.addEventListener("click", () => openSetCurrentModal(fresh));
  });
}

// ── Event listeners ───────────────────────────────────────────────────────────

function init(): void {
  attachSuggestionButtons();
  attachSetCurrentButtons();

  // Promote / demote buttons
  document.querySelectorAll<HTMLElement>(".promote-btn").forEach((btn) => {
    btn.addEventListener("click", () => openUserModal(btn, "promote"));
  });
  document.querySelectorAll<HTMLElement>(".demote-btn").forEach((btn) => {
    btn.addEventListener("click", () => openUserModal(btn, "demote"));
  });
  // Attach chapter input listeners (fields exist in hidden modals on page load)
  const setCurrentFrom = document.getElementById(
    "set-current-chapter-from",
  ) as HTMLInputElement | null;
  const setCurrentTo = document.getElementById(
    "set-current-chapter-to",
  ) as HTMLInputElement | null;
  const editFrom = document.getElementById(
    "edit-chapter-from",
  ) as HTMLInputElement | null;
  const editTo = document.getElementById(
    "edit-chapter-to",
  ) as HTMLInputElement | null;

  if (setCurrentFrom) {
    setCurrentFrom.removeEventListener("input", handleSetCurrentFromInput);
    setCurrentFrom.addEventListener("input", handleSetCurrentFromInput);
  }
  if (setCurrentTo) {
    setCurrentTo.removeEventListener("input", handleSetCurrentToInput);
    setCurrentTo.addEventListener("input", handleSetCurrentToInput);
  }
  if (editFrom) {
    editFrom.removeEventListener("input", handleEditFromInput);
    editFrom.addEventListener("input", handleEditFromInput);
  }
  if (editTo) {
    editTo.removeEventListener("input", handleEditToInput);
    editTo.addEventListener("input", handleEditToInput);
  }
}

// ── Expose globals for modal inline onclick attributes ────────────────────────

const g = window as unknown as Record<string, unknown>;
g["generateCode"] = generateCode;
g["updateAccessCode"] = updateAccessCode;
g["toggleCodeReveal"] = toggleCodeReveal;
g["copyAccessCode"] = copyAccessCode;
g["updateCurrentBook"] = updateCurrentBook;
g["completeCurrentBook"] = completeCurrentBook;
g["toggleCancellationNote"] = toggleCancellationNote;
g["saveMeeting"] = saveMeeting;
g["confirmSuggestionAction"] = confirmSuggestionAction;
g["setCurrentBook"] = setCurrentBook;
g["confirmUserAction"] = confirmUserAction;

document.addEventListener("DOMContentLoaded", init);
