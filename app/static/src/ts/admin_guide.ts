/**
 * admin_guide.ts
 * Behaviour for the collapsible admin guide (_admin_guide.html).
 */

const GUIDE_SECTIONS = ["bc", "ra", "ac", "mt", "mem"] as const;
type GuideSectionId = (typeof GUIDE_SECTIONS)[number];
const DESKTOP_BP = 640;

function getGuideEl<T extends HTMLElement>(id: string): T {
  const el = document.getElementById(id);
  if (!el) throw new Error(`AdminGuide: element #${id} not found`);
  return el as T;
}

function isDesktop(): boolean {
  return window.innerWidth >= DESKTOP_BP;
}

// ─── Outer toggle ──────────────────────────────────────────────────────────
function toggleOuter(): void {
  const body = getGuideEl("guide-body");
  const btn = getGuideEl<HTMLButtonElement>("guide-toggle-btn");
  const chevron = getGuideEl("guide-chevron");

  const isOpen = !body.classList.contains("hidden");

  if (isOpen) {
    body.classList.add("hidden");
    btn.setAttribute("aria-expanded", "false");
    chevron.classList.remove("rotate-180");
  } else {
    body.classList.remove("hidden");
    btn.setAttribute("aria-expanded", "true");
    chevron.classList.add("rotate-180");
    applyGuideLayout();
  }
}

// ─── Layout switching ──────────────────────────────────────────────────────
function applyGuideLayout(): void {
  if (isDesktop()) {
    activateDesktopLayout();
  } else {
    activateMobileLayout();
  }
}

function activateDesktopLayout(): void {
  getGuideEl("guide-panels").classList.remove("hidden");
  getGuideEl("guide-mobile").classList.add("hidden");

  const hasActive = GUIDE_SECTIONS.some(
    (s) => !getGuideEl(`dp-${s}`).classList.contains("hidden"),
  );
  if (!hasActive) selectSection("bc");
}

function activateMobileLayout(): void {
  getGuideEl("guide-panels").classList.add("hidden");
  getGuideEl("guide-mobile").classList.remove("hidden");
}

// ─── Desktop: tab selection ────────────────────────────────────────────────
function selectSection(id: GuideSectionId): void {
  GUIDE_SECTIONS.forEach((s) => {
    getGuideEl(`dp-${s}`).classList.add("hidden");
    const navBtn = getGuideEl(`nav-${s}`);
    navBtn.classList.remove("bg-gray-100", "font-semibold", "text-gray-900");
    navBtn.setAttribute("aria-selected", "false");
  });

  getGuideEl(`dp-${id}`).classList.remove("hidden");
  const activeBtn = getGuideEl(`nav-${id}`);
  activeBtn.classList.add("bg-gray-100", "font-semibold", "text-gray-900");
  activeBtn.setAttribute("aria-selected", "true");
}

// ─── Mobile: one-at-a-time accordion ───────────────────────────────────────
function toggleMobile(id: GuideSectionId): void {
  const bodyEl = getGuideEl(`mob-body-${id}`);
  const chevEl = getGuideEl(`mob-chev-${id}`);
  const btnEl = getGuideEl<HTMLButtonElement>(`mob-btn-${id}`);

  const isAlreadyOpen = !bodyEl.classList.contains("hidden");

  GUIDE_SECTIONS.forEach((s) => {
    getGuideEl(`mob-body-${s}`).classList.add("hidden");
    getGuideEl(`mob-chev-${s}`).classList.remove("rotate-180");
    getGuideEl<HTMLButtonElement>(`mob-btn-${s}`).setAttribute(
      "aria-expanded",
      "false",
    );
  });

  if (!isAlreadyOpen) {
    bodyEl.classList.remove("hidden");
    chevEl.classList.add("rotate-180");
    btnEl.setAttribute("aria-expanded", "true");
  }
}

// ─── Resize listener ───────────────────────────────────────────────────────
let resizeTimer: ReturnType<typeof setTimeout>;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    const guideBody = getGuideEl("guide-body");
    if (!guideBody.classList.contains("hidden")) {
      applyGuideLayout();
    }
  }, 120);
});

// ─── Public API (exposed to window) ────────────────────────────────────────
(window as any).AdminGuide = {
  toggleOuter,
  selectSection: (id: string) => selectSection(id as GuideSectionId),
  toggleMobile: (id: string) => toggleMobile(id as GuideSectionId),
};
