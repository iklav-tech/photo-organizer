---
name: Cyber-Metric
colors:
  surface: '#121315'
  surface-dim: '#121315'
  surface-bright: '#38393a'
  surface-container-lowest: '#0d0e0f'
  surface-container-low: '#1b1c1d'
  surface-container: '#1f2021'
  surface-container-high: '#292a2b'
  surface-container-highest: '#343536'
  on-surface: '#e3e2e3'
  on-surface-variant: '#bcc8d1'
  inverse-surface: '#e3e2e3'
  inverse-on-surface: '#303032'
  outline: '#86929a'
  outline-variant: '#3d484f'
  surface-tint: '#75d1ff'
  primary: '#92d9ff'
  on-primary: '#003548'
  primary-container: '#00c2ff'
  on-primary-container: '#004c66'
  inverse-primary: '#006688'
  secondary: '#d4bbff'
  on-secondary: '#41008b'
  secondary-container: '#6c04de'
  on-secondary-container: '#d4baff'
  tertiary: '#b8d0ff'
  on-tertiary: '#043061'
  tertiary-container: '#95b5ee'
  on-tertiary-container: '#234678'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#c2e8ff'
  primary-fixed-dim: '#75d1ff'
  on-primary-fixed: '#001e2b'
  on-primary-fixed-variant: '#004d67'
  secondary-fixed: '#ebdcff'
  secondary-fixed-dim: '#d4bbff'
  on-secondary-fixed: '#270058'
  on-secondary-fixed-variant: '#5d00c2'
  tertiary-fixed: '#d6e3ff'
  tertiary-fixed-dim: '#a9c7ff'
  on-tertiary-fixed: '#001b3d'
  on-tertiary-fixed-variant: '#244779'
  background: '#121315'
  on-background: '#e3e2e3'
  surface-variant: '#343536'
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
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
  container-max: 1280px
---

## Brand & Style
The design system is engineered for the high-performance CLI environment, bridging the gap between raw terminal efficiency and sophisticated software documentation. It targets developers and advanced enthusiasts who value precision, speed, and technical depth.

The aesthetic is **Modern-Technical with a Dark Mode focus**. It draws inspiration from high-tech circuitry and futuristic command centers, utilizing deep abyssal backgrounds contrasted with electric neon accents. The personality is authoritative yet approachable, evoking a sense of "digital mastery" over one's data. Visual elements are characterized by clean lines, glowing accents, and a systematic arrangement that suggests stability and reliability.

## Colors
The palette is rooted in a deep, nocturnal base to minimize eye strain during long technical sessions. 

- **Primary (Electric Cyan):** Used for primary actions, success states, and terminal prompts. It represents the "active" path.
- **Secondary (Neon Purple):** Used for highlights, decorative accents, and secondary CTA elements to create visual depth and a "pro" feel.
- **Tertiary (Deep Cobalt):** Used for subtle borders and container backgrounds to differentiate sections without losing the dark aesthetic.
- **Neutral:** A spectrum of cool grays starting from an almost-black foundation. Surface colors use low-light gray levels to maintain hierarchy.

## Typography
The system employs a dual-typeface strategy to separate informational content from technical execution. 

**Hanken Grotesk** is the workhorse for the UI, providing a sharp, contemporary sans-serif feel that ensures legibility in documentation and dashboard headers. It is spaced tightly for a professional look.

**JetBrains Mono** is utilized for all "technical" data, including CLI command snippets, file paths, metadata strings, and labels. This reinforces the utility of the tool and makes code-like information instantly recognizable.

## Layout & Spacing
The layout follows a **Fluid-Grid** model with high information density. 

- **Grid:** A 12-column system is used for desktop documentation, collapsing to 4 columns on mobile. 
- **Rhythm:** An 8px base unit drives all spacing to ensure a mathematical, "snapped-to-grid" feel.
- **CLI Blocks:** Code blocks and terminal outputs should span the full width of their container to maximize horizontal space for long file paths.
- **Margins:** Generous outer margins on desktop focus the user's eye on the technical content, while tight internal spacing between related data points suggests efficiency.

## Elevation & Depth
Depth is achieved through **Tonal Layering** and **Subtle Glows** rather than heavy shadows.

- **Surface Levels:** The background is the darkest level (#08090A). Each successive layer (cards, modals) uses a slightly lighter tint of blue-gray.
- **Borders:** Low-contrast cobalt outlines define the boundaries of technical sections. 
- **Luminance:** Interactive elements use an "inner glow" or a soft drop-shadow in the primary cyan color to simulate a backlit terminal screen. 
- **Backdrop Blurs:** Used sparingly behind navigation bars and modals to create a high-tech glass effect that maintains context of the data underneath.

## Shapes
The shape language is **Soft-Technical**. 

Corners are kept relatively tight (0.25rem - 0.5rem) to maintain a precise, computer-engineered appearance. Completely sharp corners are avoided to keep the interface feeling modern and premium. Progress bars and status chips may use slightly higher rounding (rounded-lg) to distinguish them from structural layout containers.

## Components
- **Buttons:** Primary buttons feature a solid Cyan fill with black text. Secondary buttons use a Cobalt ghost style with Cyan borders. Hover states should trigger a subtle outer glow.
- **CLI Snippets:** Containers with a slightly darker background than the surface, featuring a "Copy" icon in the top right. Syntax highlighting uses the secondary purple and primary cyan.
- **Status Chips:** Small, monospaced labels used for file types or process status. These use a subtle background tint of the status color (e.g., green for 'Success', amber for 'Processing').
- **Input Fields:** Dark backgrounds with a 1px border. The border glows Cyan when focused, mimicking a terminal cursor.
- **Metadata Cards:** Compact cards with thin Cobalt borders used to display photo details (ISO, Aperture, Date). Labels are monospaced and smaller than the values.
- **Data Tables:** High-density tables with no vertical borders, only thin horizontal separators, focusing on readability of file paths and organization hierarchy.