// Improved Toast System
function showToast(message, type = "success", duration = 5000) {
  const toast = document.createElement("div");
  const iconMap = {
  success: "check-circle",
  error: "x-circle",
  warning: "alert-triangle",
  info: "info",
  };

  const icon = iconMap[type] || "info";

  const bgColor =
    type === "success"
      ? "bg-green-500"
      : type === "error"
      ? "bg-red-500"
      : type === "warning"
      ? "bg-yellow-500"
      : "bg-blue-500";

  toast.className = `toast ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2`;
  toast.innerHTML = `
    <i data-lucide="${icon}" class="icon icon-sm text-white"></i>
    <span class="flex-1">${message}</span>
    <button onclick="this.parentElement.remove()" class="ml-4 text-white/80 hover:text-white">
      ×
    </button>
  `;


  const container = document.getElementById("toast-container");
  container.appendChild(toast);

  // Auto-remove after duration
  setTimeout(() => {
    if (toast.parentElement === container) {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => toast.remove(), 300);
    }
  }, duration);
}

// Mobile menu toggle
function toggleMobileMenu() {
  const menu = document.getElementById("mobile-menu");
  const menuIcon = document.getElementById("menu-icon");
  const closeIcon = document.getElementById("close-icon");

  menu.classList.toggle("hidden");
  menuIcon.classList.toggle("hidden");
  closeIcon.classList.toggle("hidden");
}

// Close mobile menu when clicking outside
document.addEventListener("click", function (event) {
  const menu = document.getElementById("mobile-menu");
  const menuButton = event.target.closest('button[aria-label="Toggle menu"]');

  if (
    !menuButton &&
    !menu.contains(event.target) &&
    !menu.classList.contains("hidden")
  ) {
    toggleMobileMenu();
  }
});

// Close mobile menu on window resize to desktop
window.addEventListener("resize", function () {
  if (window.innerWidth >= 768) {
    // md breakpoint
    const menu = document.getElementById("mobile-menu");
    const menuIcon = document.getElementById("menu-icon");
    const closeIcon = document.getElementById("close-icon");

    if (!menu.classList.contains("hidden")) {
      menu.classList.add("hidden");
      menuIcon.classList.remove("hidden");
      closeIcon.classList.add("hidden");
    }
  }
});

// Form validation helper
function validateForm(form) {
  let isValid = true;
  const errors = [];

  form.querySelectorAll("[required]").forEach((input) => {
    if (!input.value.trim()) {
      input.classList.add("border-red-500", "ring-2", "ring-red-200");
      errors.push(`${input.name || input.id} is required`);
      isValid = false;
    } else {
      input.classList.remove("border-red-500", "ring-2", "ring-red-200");
    }

    // Email validation
    if (input.type === "email" && input.value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(input.value)) {
        input.classList.add("border-red-500", "ring-2", "ring-red-200");
        errors.push("Please enter a valid email address");
        isValid = false;
      }
    }

    // Password validation
    if (input.type === "password" && input.value) {
      if (input.value.length < 8) {
        input.classList.add("border-red-500", "ring-2", "ring-red-200");
        errors.push("Password must be at least 8 characters");
        isValid = false;
      }
    }
  });

  return { isValid, errors };
}

// Track which endpoints have custom error handlers
const customErrorHandlers = new Set([
  "/auth/verify-code",
  "/auth/login",
  "/auth/register",
]);

// Global error handler for HTMX
document.addEventListener("htmx:responseError", function (event) {
  const xhr = event.detail.xhr;
  const url = event.detail.requestConfig.path;

  // Skip if this endpoint has a custom handler
  if (customErrorHandlers.has(url)) {
    return;
  }

  // Skip if we already handled it elsewhere
  if (event.detail.shouldSwap) return;

  try {
    const response = JSON.parse(xhr.response);
    const errorMsg = response.detail || "An error occurred";

    // Different handling based on status code
    switch (xhr.status) {
      case 400:
        showToast(errorMsg, "error");
        break;
      case 401:
        showToast("🔒 Please login to continue", "error");
        // Redirect to login for auth errors
        if (!url.includes("/auth/login")) {
          setTimeout(
            () => (window.location.href = "/login?error=auth_required"),
            1500
          );
        }
        break;
      case 403:
        showToast("⛔ Access denied. You need proper permissions.", "error");
        break;
      case 404:
        showToast("🔍 Resource not found", "error");
        break;
      case 422:
        showToast(`📝 ${errorMsg}`, "warning");
        break;
      default:
        showToast(`🚨 ${errorMsg}`, "error");
    }
  } catch (e) {
    // If response is not JSON - only show network error if it's a real network issue
    if (xhr.status === 0) {
      showToast("🌐 Network error. Please check your connection.", "error");
    } else {
      showToast("🚨 An unexpected error occurred. Please try again.", "error");
    }
  }
});

// Handle successful responses
document.addEventListener("htmx:afterSwap", function (event) {
  const target = event.detail.target;

  // Clear any JSON content from result divs
  if (target.id && target.id.includes("result")) {
    target.innerHTML = "";
  }
});

// Handle form submissions
document.addEventListener("htmx:beforeRequest", function (event) {
  const form = event.detail.elt;

  if (form.tagName === "FORM") {
    // Clear previous errors
    form.querySelectorAll(".border-red-500").forEach((el) => {
      el.classList.remove("border-red-500", "ring-2", "ring-red-200");
    });

    // Validate form
    const { isValid, errors } = validateForm(form);

    if (!isValid && errors.length > 0) {
      event.preventDefault();
      errors.forEach((error) => showToast(error, "warning"));
      return false;
    }

    // Add loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.innerHTML = `
        <span class="loading-spinner"></span>
        <span class="ml-2">Processing</span>
      `;

      submitBtn.disabled = true;
    }
  }
});

// Restore button state after request
document.addEventListener("htmx:afterRequest", function (event) {
  const xhr = event.detail.xhr;
  const target = event.detail.target;

  // Don't process if it's an error (handled elsewhere)
  if (xhr.status >= 400) return;

  // Check if response is JSON
  const contentType = xhr.getResponseHeader("Content-Type");
  if (contentType && contentType.includes("application/json")) {
    try {
      const data = JSON.parse(xhr.responseText);

      // Show toast for successful operations
      if (data.message && xhr.status >= 200 && xhr.status < 300) {
        showToast(data.message, "success");

        // Clear any target content
        if (target) {
          target.innerHTML = "";
        }

        // Handle specific redirects if needed
        if (data.redirect) {
          setTimeout(() => {
            window.location.href = data.redirect;
          }, 1500);
        }

        // Handle page reloads if needed
        if (data.reload) {
          setTimeout(() => location.reload(), 1500);
        }
      }
    } catch (e) {
      // Not JSON, ignore
    }
  }
});

// On page load, check for URL error parameters
document.addEventListener("DOMContentLoaded", function () {
  const urlParams = new URLSearchParams(window.location.search);
  const error = urlParams.get("error");

  const errorMessages = {
    access_required: "🔒 Please enter the access code first",
    verify_code_first: "🔑 Please verify access code before registering",
    login_required: "🔒 Please login to continue",
    access_denied: "⛔ Access denied. You need proper permissions.",
    page_not_found: "🔍 Page not found",
    validation_error: "📝 Please check your input and try again",
    server_error: "🚨 An unexpected error occurred. Please try again.",
    auth_required: "🔒 Authentication required. Please login.",
    invalid_credentials: "❌ Invalid email or password",
  };

  if (error && errorMessages[error]) {
    showToast(
      errorMessages[error],
      error === "access_required" || error === "verify_code_first"
        ? "warning"
        : "error"
    );

    // Clean URL (remove error parameter)
    const newUrl = window.location.pathname;
    window.history.replaceState({}, document.title, newUrl);
  }

  // Store original button text
  document.querySelectorAll('button[type="submit"]').forEach((btn) => {
    btn.setAttribute("data-original-text", btn.innerHTML);
  });
});

document.addEventListener("htmx:configRequest", (evt) => {
  // Disable button + add spinner on ALL HTMX requests
  const button =
    evt.detail.elt.closest("button") ||
    evt.detail.elt.querySelector('button[type="submit"]');
  if (button) {
    button.disabled = true;
    button.classList.add("btn-loading");
    button.innerHTML =
      button.innerHTML.replace("::after", "") +
      ' <span class="loading-spinner"></span>';
  }
});

document.addEventListener("htmx:afterRequest", (evt) => {
  // Re-enable buttons after ALL requests
  document.querySelectorAll(".btn-loading").forEach((btn) => {
    btn.disabled = false;
    btn.classList.remove("btn-loading");
    // Remove spinner, restore original text
    btn.innerHTML = btn.innerHTML.replace(
      /<span class="loading-spinner"><\/span>$/,
      ""
    );
  });
});

function initIcons() {
  if (window.lucide) {
    lucide.createIcons();
  }
}

// Initial load
document.addEventListener("DOMContentLoaded", initIcons);

// Re-run after HTMX swaps
document.addEventListener("htmx:afterSwap", initIcons);

