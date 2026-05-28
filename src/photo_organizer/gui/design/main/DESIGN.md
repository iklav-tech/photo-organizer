---
name: Cyber-Metric
colors:
  surface: '#121315'
  surface-dim: '#121315'
  surface-bright: '#38393b'
  surface-container-lowest: '#0d0e10'
  surface-container-low: '#1b1c1e'
  surface-container: '#1f2022'
  surface-container-high: '#292a2c'
  surface-container-highest: '#343537'
  on-surface: '#e3e2e4'
  on-surface-variant: '#bfc8ce'
  inverse-surface: '#e3e2e4'
  inverse-on-surface: '#303032'
  outline: '#899298'
  outline-variant: '#40484d'
  surface-tint: '#88cff5'
  primary: '#d8f0ff'
  on-primary: '#003548'
  primary-container: '#92d9ff'
  on-primary-container: '#006080'
  inverse-primary: '#066687'
  secondary: '#d4bbff'
  on-secondary: '#39255e'
  secondary-container: '#533e78'
  on-secondary-container: '#c5adf0'
  tertiary: '#e6ecff'
  on-tertiary: '#163056'
  tertiary-container: '#b9d1ff'
  on-tertiary-container: '#425982'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#c2e8ff'
  primary-fixed-dim: '#88cff5'
  on-primary-fixed: '#001e2b'
  on-primary-fixed-variant: '#004d67'
  secondary-fixed: '#ebdcff'
  secondary-fixed-dim: '#d4bbff'
  on-secondary-fixed: '#240d48'
  on-secondary-fixed-variant: '#503c76'
  tertiary-fixed: '#d6e3ff'
  tertiary-fixed-dim: '#afc7f6'
  on-tertiary-fixed: '#001b3e'
  on-tertiary-fixed-variant: '#2f476e'
  background: '#121315'
  on-background: '#e3e2e4'
  surface-variant: '#343537'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  sidebar_width: 280px
  inspector_width: 320px
  gutter: 24px
---

## Brand & Style

The design system is a high-performance, technical aesthetic engineered for digital asset management. It bridges the gap between terminal-based efficiency and professional creative tooling, similar to a "dark room" environment where the interface recedes to let the content—photographs—take center stage.

The style is a hybrid of **Minimalism** and **Modern Corporate**, utilizing high-density layouts and a precise, mathematical rhythm. It evokes a sense of **Digital Mastery** through the use of deep nocturnal surfaces, sharp electric accents, and technical monospaced typography. The emotional response is one of reliability, precision, and absolute control over complex data structures.

- **Atmosphere:** Authoritative, technical, focused, and nocturnal.
- **Visual Strategy:** Use dark, low-luminance surfaces to minimize eye strain and maximize photo color fidelity.
- **Interactions:** Tactile glowing states and high-contrast borders provide clear feedback in a dense environment.

## Colors

The palette is anchored in a **Nocturnal Background** to support professional photo editing and organization workflows. 

- **Primary (Electric Cyan):** Used for critical actions, active states, and primary focal points like the 'Organize' button.
- **Secondary (Neon Purple):** Reserved for secondary calls to action and "pro" level metadata highlights.
- **Neutral Hierarchy:** Surfaces are layered from the deepest background (`#08090a`) to elevated containers (`#1b1c1d`), using subtle luminosity shifts rather than heavy shadows to define depth.
- **Functional Colors:** Success, Warning, and Error colors are used sparingly for terminal logs and status badges, ensuring they are visible against the dark canvas without being jarring.

## Typography

This design system employs a dual-font strategy to balance user-friendly navigation with technical precision.

- **Hanken Grotesk:** Used for the main UI framework, headers, and primary body text. Its geometric clarity provides a modern, professional feel.
- **JetBrains Mono:** Used for all technical data, including file paths, EXIF metadata (ISO, Aperture), and execution logs. The monospaced nature emphasizes the utility and "engineered" feel of the tool.

Keep line heights tight for headers to maintain density, while allowing body text more breathing room. Use `label-sm` (monospaced) for metadata badges and file extensions to differentiate them from functional UI labels.

## Layout & Spacing

The layout is a **Three-Pane Fixed Grid** model, optimized for high-density desktop utility.

1.  **Navigation Sidebar (Left):** 280px fixed width. Contains the app brand, primary navigation, and library filters.
2.  **Main Canvas (Center):** Fluid width. A dynamic grid hosting photo thumbnails. As the window expands, the number of columns should increase while maintaining a minimum thumbnail size.
3.  **Metadata Inspector (Right):** 320px fixed width. A vertical panel for detailed EXIF data and batch action configurations.

**Spacing Rhythm:** 
- Use a base unit of **4px**. 
- Standard component padding is **8px** (internal) and **16px** (external). 
- Panes are separated by **1px borders** rather than wide gutters to maximize screen real estate for photos.

## Elevation & Depth

Visual hierarchy is established through **Tonal Layering** and **High-Contrast Outlines** rather than traditional shadows.

- **Layering:** The base window uses the darkest hex (`#08090a`). Sidebars and cards sit on top using slightly lighter surfaces (`#121315` and `#1b1c1d`).
- **Borders:** Use 1px low-contrast outlines (`#3d484f`) to define the boundaries of cards, panels, and input fields.
- **Active Elevation:** When an element is focused or selected (like a photo thumbnail), replace the neutral border with an **Electric Cyan** (`#92d9ff`) border. 
- **Interactive Glow:** For primary buttons and selected thumbnails, apply a very subtle, soft-glow (backdrop-tint) using the primary color at 15% opacity to simulate an "active light" effect common in professional hardware consoles.

## Shapes

The design system uses a **Soft** roundedness profile to maintain a professional, precision-tool appearance. 

- **Standard Elements:** Buttons, input fields, and cards use a `0.25rem` (4px) radius.
- **Large Elements:** Larger containers or modal dialogs may scale up to `0.5rem` (8px).
- **Photo Thumbnails:** Should remain strictly at `0.25rem` to prevent the UI from feeling too "consumer" or "playful," ensuring the focus remains on the rectangular nature of photographs.

## Components

### Buttons
- **Primary ('Organize'):** Solid `#92d9ff` fill with `#003548` text. High-contrast and bold.
- **Secondary ('Select Folder'):** Ghost style with `#86929a` border and `#e3e2e3` text.
- **Hover States:** Borders should transition to the primary or secondary accent color, accompanied by a subtle increase in surface luminosity.

### Photo Thumbnail Cards
- High-density square cards.
- **Background:** `#1b1c1d`.
- **Label:** File name in `JetBrains Mono` at the bottom of the card on a semi-transparent `#0d0e0f` overlay.
- **Selected State:** 2px solid `#92d9ff` border.

### Sidebar Navigation
- Icons should be minimal (Material Symbols or similar).
- **Active State:** Inset 3px vertical border on the far left edge using `#92d9ff` and a background tint of `rgba(0, 194, 255, 0.1)`.

### Input Fields & Controls
- **Fields:** Surface `#1b1c1d` with `#3d484f` border.
- **Checkboxes:** Square with `#92d9ff` fill when checked.
- **Progress Bars:** 6px height. Track: `#343536`. Fill: `#92d9ff` with a slight outer glow.

### Technical Logs (Console)
- A bottom-aligned sunken panel using `#0d0e0f`. 
- Text is exclusively `JetBrains Mono` 14px.
- Use Mint (`#9ff2bd`), Amber (`#ffd98a`), and Coral (`#ffb4ab`) for status-specific log lines.