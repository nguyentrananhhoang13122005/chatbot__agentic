---
name: Riso
colors:
  primary: "#F237A1"
  secondary: "#2C40A7"
  success: "#16A34A"
  warning: "#D97706"
  danger: "#DC2626"
  surface: "#FFFFFF"
  text: "#111827"
  neutral: "#FFFFFF"
typography:
  h1:
    fontFamily: "Space Grotesk"
    fontSize: 2rem
  body-md:
    fontFamily: "Space Grotesk"
    fontSize: 1rem
  label-caps:
    fontFamily: "Overpass Mono"
    fontSize: 0.75rem
  sourceScale: "12/14/16/20/24/32"
  weights: "100, 200, 300, 400, 500, 600, 700, 800, 900"
rounded:
  sm: 4px
  md: 8px
spacing:
  sm: 4px
  md: 8px
  sourceScale: "4/8/12/16/24/32"
---

## Overview

Playful two-color risograph-inspired system with paper-like warmth, vivid pink actions, and bold blue structure.

## Style Foundations

- **Visual style:** clean, high-contrast
- **Typography scale:** 12/14/16/20/24/32
- **Typography fonts:** primary=Space Grotesk, display=Space Grotesk, mono=Overpass Mono
- **Typography weights:** 100, 200, 300, 400, 500, 600, 700, 800, 900
- **Color palette:** primary, secondary
- **Spacing scale:** 4/8/12/16/24/32

## Colors

- **Primary (#F237A1):** Token from style foundations.
- **Secondary (#2C40A7):** Token from style foundations.
- **Success (#16A34A):** Token from style foundations.
- **Warning (#D97706):** Token from style foundations.
- **Danger (#DC2626):** Token from style foundations.
- **Surface (#FFFFFF):** Token from style foundations.
- **Text (#111827):** Token from style foundations.
- **Neutral (#FFFFFF):** Derived from the surface token for official format compatibility.

## Dark Mode Colors

- **Surface (#18181B):** Neutral dark surface — desaturated, sophisticated.
- **Paper (#111113):** Deeper variant for backgrounds and sidebar.
- **Surface-Raised (#222226):** Elevated surface for cards, popovers, inputs.
- **Text (#EDEDF0):** Clean light text for readability on dark surfaces.
- **Text-Secondary (#8B8B94):** Muted gray for secondary info, labels, timestamps.
- **Border (#2E2E33):** Subtle neutral border — refined, not heavy.
- **Neutral (#18181B):** Matches dark surface.
- **Primary (#F237A1):** Unchanged — vivid pink stays vibrant on dark.
- **Secondary (#2C40A7):** Unchanged — bold blue stays vibrant on dark.
- **hl-blue (#6B82F0):** Brightened blue for hero text on dark backgrounds.

### Shadow System (Dark Mode)
- **riso-shadow:** Ambient glow `0 2px 8px rgba(0,0,0,0.4)` + hairline border
- **riso-shadow-hover:** Pink glow `0 4px 20px rgba(242,55,161,0.18)` + pink border
- **glow-primary:** `0 0 20px rgba(242,55,161,0.15)` — for primary buttons & focus
- **glow-secondary:** `0 0 20px rgba(44,64,167,0.15)` — for headers & accents

### Toggle Behavior
- Default: Light mode (Riso paper-like warmth)
- Toggle via sidebar button (🌙/☀️)
- Persisted in `st.session_state` + `localStorage` for anti-flash