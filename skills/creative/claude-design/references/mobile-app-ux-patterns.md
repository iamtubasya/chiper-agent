# Mobile App-Like UX Patterns for Web Applications

This guide provides tested patterns when transforming responsive desktop dashboards into modern, native-feeling mobile web experiences.

## 1. Floating Bottom Navigation Dock

Desktop dashboards typically rely on left-hand sidebars. On mobile screens (< 1024px), hiding all navigation inside a top-left hamburger menu creates high friction. Adding a bottom dock mirrors native mobile navigation (iOS/Android):

```html
<nav class="mobile-dock" aria-label="Mobile Navigation">
  <a href="/endpoint" class="dock-item active">
    <div class="dock-icon-wrap"><span class="icon">api</span></div>
    <span class="dock-label">Endpoint</span>
  </a>
  <a href="/providers" class="dock-item">
    <div class="dock-icon-wrap"><span class="icon">dns</span></div>
    <span class="dock-label">Providers</span>
  </a>
  <!-- Core actions (4 items max) + 1 Menu button for secondary links -->
  <button type="button" class="dock-item" id="dock-menu-btn">
    <div class="dock-icon-wrap"><span class="icon">menu</span></div>
    <span class="dock-label">Menu</span>
  </button>
</nav>
```

### Essential Mobile Dock CSS

```css
@media (max-width: 1023px) {
  .mobile-dock {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: calc(62px + env(safe-area-inset-bottom, 0px));
    padding-bottom: env(safe-area-inset-bottom, 0px);
    background: rgba(8, 12, 22, 0.94);
    backdrop-filter: blur(28px);
    -webkit-backdrop-filter: blur(28px);
    border-top: 1px solid rgba(0, 242, 254, 0.2);
    box-shadow: 0 -10px 35px rgba(0, 0, 0, 0.8);
    z-index: 9999;
    align-items: center;
    justify-content: space-around;
  }

  /* Prevent bottom content from being obscured */
  main, .page-scroll-container {
    padding-bottom: calc(85px + env(safe-area-inset-bottom, 0px)) !important;
  }
}

@media (min-width: 1024px) {
  .mobile-dock {
    display: none !important;
  }
}
```

---

## 2. Tailwind CSS v4 `translate` Property Pitfall

In Tailwind v4, `-translate-x-full` compiles to the independent CSS property `translate: -100% 0` (or `translate: -100%`), NOT standard `transform: translateX(-100%)`.

If overriding or controlling a slide-out drawer via JavaScript or custom CSS:
```css
/* WRONG (fails in Tailwind v4 because `translate` property remains -100%): */
.drawer-open {
  transform: translateX(0) !important;
}

/* CORRECT (overrides modern CSS `translate` property and CSS variables): */
.drawer-open {
  translate: 0 0 !important;
  --tw-translate-x: 0 !important;
  transform: none !important;
  left: 0 !important;
}
```

---

## 3. Drawer Stacking & Backdrop Blur Bleed

When rendering a slide-out drawer alongside a full-screen dimmed backdrop:
1. **Backdrop Filter Trap:** Applying `backdrop-filter: blur(...)` to a full-screen backdrop appended to `document.body` can inadvertently blur the drawer itself if the drawer is nested inside a container with `isolation: isolate` or `overflow: hidden`.
2. **Layer Ordering:** Keep the backdrop clean (`background: rgba(0, 0, 0, 0.72)`) without heavy full-screen filter blurs, and ensure the drawer has a higher z-index (e.g. `z-index: 10002`) than the backdrop (`z-index: 10001`).

---

## 4. Touch Form Optimization
- Set form input `font-size: 16px !important;` on screens < 768px. Anything below 16px triggers automatic viewport zooming in iOS Safari.
- Minimum touch target for tap buttons: 44px × 44px.
