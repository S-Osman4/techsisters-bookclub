// ========================================
// UNIFIED MODAL SYSTEM
// ========================================

/**
 * Global modal state management
 */
let currentBookIdForModal = null;
let currentBookData = {};
let currentSuggestionId = null;
let currentAction = null;

/**
 * Open any modal by ID
 */
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('hidden');
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
  }
}

/**
 * Close any modal by ID
 */
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('hidden');
    // Restore body scroll
    document.body.style.overflow = '';
    
    // Reset form if exists
    const form = modal.querySelector('form');
    if (form) form.reset();
    
    // Clear result messages
    const results = modal.querySelectorAll('[id$="-result"]');
    results.forEach(el => el.innerHTML = '');
  }
}

/**
 * Close all open modals
 */
function closeAllModals() {
  document.querySelectorAll('.modal-overlay:not(.hidden)').forEach(modal => {
    closeModal(modal.id);
  });
}

// ========================================
// KEYBOARD SHORTCUTS
// ========================================

document.addEventListener('keydown', function(e) {
  // Close modals on Escape
  if (e.key === 'Escape') {
    closeAllModals();
  }
});

// ========================================
// ACCESS CODE MODAL
// ========================================

function generateCode() {
  fetch("/api/admin/code/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (!response.ok) throw new Error("Failed to generate code");
      return response.json();
    })
    .then((data) => {
      const input = document.getElementById("new-code-input");
      if (input && data.code) {
        input.value = data.code;
        showToast("New code generated", "success");
      } else {
        showToast("Could not read generated code", "error");
      }
    })
    .catch((error) => {
      showToast("Error generating code: " + error.message, "error");
    });
}

// ========================================
// COMPLETE BOOK MODAL
// ========================================

function completeCurrentBook() {
  const resultDiv = document.getElementById('complete-result');
  resultDiv.innerHTML = '<div class="text-sm text-gray-500 text-center">Processing...</div>';
  
  fetch('/api/admin/books/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        resultDiv.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
        showToast(data.message, 'success');
        setTimeout(() => {
          closeModal('complete-modal');
          window.location.reload();
        }, 1000);
      } else {
        resultDiv.innerHTML = `<div class="alert alert-error">${data.message}</div>`;
        showToast(data.message, 'error');
      }
    })
    .catch(error => {
      resultDiv.innerHTML = `<div class="alert alert-error">Error: ${error.message}</div>`;
      showToast('Error: ' + error.message, 'error');
    });
}

// ========================================
// SUGGESTION REVIEW MODAL
// ========================================

/**
 * Preview cover image as user types
 */
function previewCover(url) {
  const preview = document.getElementById("modal-cover-preview");
  const warning = document.getElementById("no-cover-warning");
  const status = document.getElementById("cover-status");
  
  if (!url || url.trim() === "") {
    preview.innerHTML = '<span class="text-4xl">📚</span>';
    status.textContent = "";
    if (currentAction === "approve") {
      warning.classList.remove("hidden");
    }
    return;
  }
  
  warning.classList.add("hidden");
  status.textContent = "Loading preview...";
  
  const img = new Image();
  img.onload = function() {
    preview.innerHTML = `<img src="${url}" alt="Book cover" class="w-full h-full object-cover" />`;
    status.innerHTML = '<span style="color: var(--secondary);">✓ Cover loaded successfully</span>';
  };
  img.onerror = function() {
    preview.innerHTML = '<span class="text-4xl">📚</span>';
    status.innerHTML = '<span style="color: var(--primary);">⚠ Could not load image</span>';
  };
  img.src = url;
}

/**
 * Open suggestion modal with data
 */
function openSuggestionModal(id, title, userName, userEmail, pdfUrl, coverUrl, action) {
  currentSuggestionId = id;
  currentAction = action;

  document.getElementById("suggestion-id").value = id;
  document.getElementById("action-type").value = action;
  document.getElementById("suggestion-title").textContent = title;
  document.getElementById("suggestion-user").textContent = `Suggested by ${userName} (${userEmail})`;
  document.getElementById("suggestion-pdf").href = pdfUrl;

  const modalTitle = document.getElementById("suggestion-modal-title");
  const confirmBtn = document.getElementById("confirm-action-btn");
  const btnText = document.getElementById("btn-text");
  const coverInput = document.getElementById("cover-url-input");
  const coverSection = document.getElementById("cover-input-section");
  const warning = document.getElementById("no-cover-warning");
  const coverRequired = document.getElementById("cover-required");

  if (action === "approve") {
    modalTitle.textContent = `✅ Approve "${title}"`;
    btnText.textContent = "✓ Approve & Add to Queue";
    confirmBtn.className = "btn btn-secondary";
    coverSection.classList.remove("hidden");
    coverRequired.classList.remove("hidden");
    warning.classList.toggle("hidden", !!coverUrl);
  } else {
    modalTitle.textContent = `❌ Reject "${title}"`;
    btnText.textContent = "✗ Reject Suggestion";
    confirmBtn.className = "btn btn-danger";
    coverSection.classList.add("hidden");
    warning.classList.add("hidden");
  }

  coverInput.value = coverUrl || "";
  if (coverUrl) {
    previewCover(coverUrl);
  } else {
    document.getElementById("modal-cover-preview").innerHTML = '<span class="text-4xl">📚</span>';
  }
  
  document.getElementById("suggestion-result").innerHTML = "";
  openModal('suggestion-modal');
}

/**
 * Close suggestion modal
 */
function closeSuggestionModal() {
  closeModal('suggestion-modal');
  currentSuggestionId = null;
  currentAction = null;
}

/**
 * Handle suggestion form submission
 */
async function handleSuggestionAction(e) {
  e.preventDefault();

  const coverUrl = document.getElementById("cover-url-input").value.trim();
  const resultDiv = document.getElementById("suggestion-result");
  const suggestionId = document.getElementById("suggestion-id").value;
  const action = document.getElementById("action-type").value;
  const confirmBtn = document.getElementById("confirm-action-btn");
  const btnText = document.getElementById("btn-text");

  if (action === "approve" && !coverUrl) {
    resultDiv.innerHTML = '<div class="alert alert-error"><strong>⚠️ Missing Cover:</strong> Please add a cover image URL to approve this book</div>';
    return;
  }

  confirmBtn.disabled = true;
  btnText.innerHTML = '<span class="loading-spinner">Processing</span>';
  resultDiv.innerHTML = '<div class="text-sm text-gray-500 text-center">Processing your request...</div>';

  try {
    const formData = new FormData();
    if (action === "approve") {
      formData.append("cover_image_url", coverUrl);
    }

    const response = await fetch(`/api/admin/suggestions/${suggestionId}/${action}`, {
      method: "PUT",
      body: formData
    });

    const data = await response.json();

    if (data.success) {
      resultDiv.innerHTML = `<div class="alert alert-success"><strong>✓ Success:</strong> ${data.message}</div>`;
      showToast(data.message, "success");
      setTimeout(() => {
        closeSuggestionModal();
        location.reload();
      }, 800);
    } else {
      resultDiv.innerHTML = `<div class="alert alert-error"><strong>✗ Error:</strong> ${data.message || "Something went wrong"}</div>`;
      confirmBtn.disabled = false;
      btnText.textContent = action === "approve" ? "✓ Approve & Add to Queue" : "✗ Reject Suggestion";
    }
  } catch (err) {
    resultDiv.innerHTML = `<div class="alert alert-error"><strong>✗ Error:</strong> ${err.message}</div>`;
    confirmBtn.disabled = false;
    btnText.textContent = action === "approve" ? "✓ Approve & Add to Queue" : "✗ Reject Suggestion";
  }
}

// ========================================
// SET CURRENT BOOK MODAL
// ========================================

/**
 * Preview cover image for current book
 */
function previewCurrentCover(url) {
  const preview = document.getElementById("current-cover-preview");
  const status = document.getElementById("current-cover-status");
  
  if (!url || url.trim() === "") {
    if (currentBookData.originalCover) {
      preview.innerHTML = `<img src="${currentBookData.originalCover}" alt="Book cover" class="w-full h-full object-cover" />`;
      status.innerHTML = '<span style="color: var(--secondary);">✓ Using original cover</span>';
    } else {
      preview.innerHTML = '<span class="text-4xl">📚</span>';
      status.textContent = "";
    }
    return;
  }
  
  status.textContent = "Loading preview...";
  
  const img = new Image();
  img.onload = function() {
    preview.innerHTML = `<img src="${url}" alt="Book cover" class="w-full h-full object-cover" />`;
    status.innerHTML = '<span style="color: var(--secondary);">✓ New cover loaded successfully</span>';
  };
  img.onerror = function() {
    if (currentBookData.originalCover) {
      preview.innerHTML = `<img src="${currentBookData.originalCover}" alt="Book cover" class="w-full h-full object-cover" />`;
      status.innerHTML = '<span style="color: var(--primary);">⚠ Could not load new image - showing original</span>';
    } else {
      preview.innerHTML = '<span class="text-4xl">📚</span>';
      status.innerHTML = '<span style="color: var(--primary);">⚠ Could not load image</span>';
    }
  };
  img.src = url;
}

/**
 * Open Set Current Book modal
 */
function openSetCurrentModal(bookId, title, coverUrl = "", pdfUrl = "") {
  currentBookIdForModal = bookId;
  currentBookData = {
    id: bookId,
    title: title,
    originalCover: coverUrl,
    pdfUrl: pdfUrl
  };

  const subtitle = document.getElementById("set-current-subtitle");
  const bookTitle = document.getElementById("current-book-title");
  const bookPdf = document.getElementById("current-book-pdf");
  const coverInput = document.getElementById("current-cover-url-input");
  const preview = document.getElementById("current-cover-preview");
  const status = document.getElementById("current-cover-status");

  subtitle.textContent = `Configure "${title}" as the club's current read`;
  bookTitle.textContent = title;
  
  if (pdfUrl) {
    bookPdf.href = pdfUrl;
    bookPdf.classList.remove("hidden");
  } else {
    bookPdf.classList.add("hidden");
  }

  const form = document.getElementById("set-current-form");
  form.reset();
  
  coverInput.value = coverUrl || "";
  
  if (coverUrl) {
    preview.innerHTML = `<img src="${coverUrl}" alt="${title}" class="w-full h-full object-cover" />`;
    status.innerHTML = '<span style="color: var(--secondary);">✓ Current cover loaded</span>';
  } else {
    preview.innerHTML = '<span class="text-4xl">📚</span>';
    status.textContent = "";
  }

  document.getElementById("set-current-result").innerHTML = "";
  openModal('set-current-modal');
}

/**
 * Close Set Current Book modal
 */
function closeSetCurrentModal() {
  closeModal('set-current-modal');
  currentBookIdForModal = null;
  currentBookData = {};
}

/**
 * Handle Set Current Book form submission
 */
function onSetCurrentSubmit(event) {
  event.preventDefault();

  const form = document.getElementById("set-current-form");
  const currentChapters = form.querySelector('[name="current_chapters"]').value;
  const coverImageUrl = form.querySelector('[name="cover_image_url"]').value;
  const totalChapters = form.querySelector('[name="total_chapters"]').value;
  const resultDiv = document.getElementById("set-current-result");
  const submitBtn = document.getElementById("set-current-btn");
  const btnText = document.getElementById("set-current-btn-text");

  if (!currentChapters || !currentChapters.trim()) {
    resultDiv.innerHTML = '<div class="alert alert-error"><strong>⚠️ Required:</strong> Please specify the current chapters</div>';
    return false;
  }

  submitBtn.disabled = true;
  btnText.innerHTML = '<span class="loading-spinner">Setting</span>';
  resultDiv.innerHTML = '<div class="text-sm text-gray-500 text-center">Setting book as current...</div>';

  fetch(`/api/admin/books/${currentBookIdForModal}/set-current`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_chapters: currentChapters.trim(),
      cover_image_url: coverImageUrl.trim() || null,
      total_chapters: totalChapters ? parseInt(totalChapters) : null,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        resultDiv.innerHTML = `<div class="alert alert-success"><strong>✓ Success:</strong> ${data.message}</div>`;
        showToast(data.message, "success");
        setTimeout(() => {
          closeSetCurrentModal();
          window.location.reload();
        }, 1000);
      } else {
        resultDiv.innerHTML = `<div class="alert alert-error"><strong>✗ Error:</strong> ${data.message || "Something went wrong"}</div>`;
        submitBtn.disabled = false;
        btnText.textContent = "✓ Set as Current Book";
      }
    })
    .catch((error) => {
      resultDiv.innerHTML = `<div class="alert alert-error"><strong>✗ Error:</strong> ${error.message}</div>`;
      submitBtn.disabled = false;
      btnText.textContent = "✓ Set as Current Book";
    });

  return false;
}

// ========================================
// USER MANAGEMENT
// ========================================

function promoteUser(userId, userName) {
  if (confirm(`Promote ${userName} to admin?\n\nThey will be able to:\n• Manage books and meetings\n• Approve/reject suggestions\n• Access admin panel`)) {
    fetch(`/api/admin/users/${userId}/promote`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
    })
      .then((response) => response.json())
      .then((data) => {
        showToast(data.message, data.success ? "success" : "error");
        if (data.success) {
          setTimeout(() => location.reload(), 1500);
        }
      })
      .catch((error) => {
        showToast("Error: " + error.message, "error");
      });
  }
}

function demoteUser(userId, userName) {
  if (confirm(`Demote ${userName} from admin?\n\nThey will lose access to:\n• Admin panel\n• Book/meeting management\n• Suggestion approval`)) {
    fetch(`/api/admin/users/${userId}/demote`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
    })
      .then((response) => response.json())
      .then((data) => {
        showToast(data.message, data.success ? "success" : "error");
        if (data.success) {
          setTimeout(() => location.reload(), 1500);
        }
      })
      .catch((error) => {
        showToast("Error: " + error.message, "error");
      });
  }
}

// ========================================
// EVENT LISTENERS
// ========================================

document.addEventListener('DOMContentLoaded', function() {
  // Approve buttons
  document.querySelectorAll('.approve-btn').forEach(button => {
    button.addEventListener('click', function() {
      const data = this.dataset;
      openSuggestionModal(
        data.id,
        data.title,
        data.userName,
        data.userEmail,
        data.pdfUrl,
        data.coverUrl,
        'approve'
      );
    });
  });

  // Reject buttons
  document.querySelectorAll('.reject-btn').forEach(button => {
    button.addEventListener('click', function() {
      const data = this.dataset;
      openSuggestionModal(
        data.id,
        data.title,
        data.userName,
        data.userEmail,
        data.pdfUrl,
        data.coverUrl,
        'reject'
      );
    });
  });

  // Attach suggestion form handler
  const suggestionForm = document.getElementById("suggestion-form");
  if (suggestionForm) {
    suggestionForm.addEventListener("submit", handleSuggestionAction);
  }

  // HTMX after-swap handlers
  document.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target.id === "code-result" ||
        event.detail.target.id === "edit-result" ||
        event.detail.target.id === "meeting-result") {
      showToast("Changes saved successfully!", "success");
      setTimeout(() => location.reload(), 1000);
    }
  });
});