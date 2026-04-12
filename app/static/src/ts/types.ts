// app/static/src/ts/types.ts

export type ToastType = "success" | "error" | "warning" | "info";

export interface ApiResponse {
  message?: string;
  detail?: string;
  success?: boolean;
  redirect?: string;
}

export interface HtmxRequestConfig {
  path: string;
  verb: string;
  target: Element;
  elt: Element;
}

// Augment the window object with HTMX types
declare global {
  interface Window {
    htmx: {
      on(event: string, handler: (evt: CustomEvent) => void): void;
      trigger(elt: Element, event: string): void;
    };
    lucide: {
      createIcons(): void;
    };
  }
}
