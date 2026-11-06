---
name: modern-frontend-development
description: Production-grade frontend development with React, Next.js, Vite, Tailwind CSS, shadcn/ui, responsive layouts, and accessible UI components.
category: software-development
---

# Modern Frontend Development (React, Next.js, Tailwind & UI Systems)

Build resilient, accessible, and high-performance Web UIs. Designed for modern React ecosystems (Next.js App Router, Vite) using Tailwind CSS and composable component systems.

---

## 1. Trigger Conditions

Load this skill when:
- Creating or refactoring web user interfaces (dashboards, chat portals, landing pages, forms).
- Structuring React or Next.js applications (App Router, Server vs Client components).
- Applying Tailwind CSS utility classes, design tokens, responsive breakpoints, or dark/light themes.
- Integrating UI component libraries (shadcn/ui, Radix UI, Lucide icons, Headless UI).
- Implementing frontend state management (Zustand, React Query/TanStack, Context API).

---

## 2. Core Architecture Standards

### Next.js App Router Rules (Server vs Client Components)
- **Server Component by default:** Fetch data, read headers, access backend resources.
- **Client Component (`"use client"`):** Use only when state (`useState`), effects (`useEffect`), event handlers (`onClick`, `onChange`), or browser APIs (DOM, localStorage) are needed.
- **Push `"use client"` to leaves:** Wrap only the interactive button or input in `"use client"`, keeping parent layouts and data wrappers as Server Components.
- **Zero Hydration Mismatch:** Never render browser-dependent content (`Date.now()`, `window.innerWidth`, `localStorage`) directly during initial server render. Use an `isMounted` state or `useEffect` mount gate.

### Styling & Design System (Tailwind CSS)
- **Utility First, Token Driven:** Use semantic color tokens (`bg-background text-foreground border-border`) instead of hardcoded hex values (`bg-[#121212]`).
- **Mobile-First Responsive Layouts:**
  - Base classes apply to mobile (`w-full flex-col`).
  - Breakpoints expand upward (`md:flex-row md:w-1/2 lg:w-1/3`).
- **Interactive States:** Always provide explicit `:hover`, `:focus-visible`, and `:disabled` styling for interactive elements.
- **Dark Mode Support:** Ensure dark mode styling is baked in with `dark:*` variants or root CSS variable transitions.

### Accessibility (a11y) & Semantic HTML
- **Semantic Tags:** Use `<main>`, `<nav>`, `<aside>`, `<header>`, `<footer>`, `<button>`, `<section>` instead of `<div>` soup.
- **ARIA & Keyboard Navigation:** Form inputs must have matching `<label>` elements or `aria-label`. Modals and drawers must support `Escape` to close and trap focus.
- **No Icon-Only Buttons without Labels:** Every icon button (`<button><TrashIcon /></button>`) must include `aria-label="Delete item"` or `<span className="sr-only">Delete</span>`.

---

## 3. High-Quality Component Patterns

### Composable Card Pattern
```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "cyber" | "outline";
}

export function Card({ className, variant = "default", children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border p-6 transition-all duration-200",
        variant === "default" && "bg-card text-card-foreground border-border shadow-sm",
        variant === "cyber" && "bg-zinc-950/80 border-cyan-500/30 text-zinc-100 shadow-[0_0_15px_rgba(6,182,212,0.15)]",
        variant === "outline" && "border-zinc-800 bg-transparent text-zinc-200",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
```

### Real-time Streaming Chat Bubble Pattern
```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
  isStreaming?: boolean;
}

export function ChatMessage({ role, content, isStreaming }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={cn("flex w-full mb-4", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-cyan-600 text-white rounded-tr-none shadow-md"
            : "bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-tl-none shadow-sm"
        )}
      >
        <div className="whitespace-pre-wrap break-words">{content}</div>
        {isStreaming && (
          <span className="inline-block w-2 h-4 ml-1 bg-cyan-400 animate-pulse align-middle" />
        )}
      </div>
    </div>
  );
}
```

---

## 4. Verification & Testing

Before declaring UI work done:
1. **Linter & Type Check:** Run `npm run lint` or `tsc --noEmit` to ensure clean types with no `@ts-ignore`.
2. **Bundle & Build Check:** Run `npm run build` or `vite build` to verify zero production build errors.
3. **Visual & Console Inspection:** Open in browser or verify via `agent-browser` that:
   - Console has 0 unhandled exceptions or hydration warnings.
   - Layout is responsive across mobile (375px), tablet (768px), and desktop (1280px).
