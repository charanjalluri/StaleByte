---
name: StaleByte
description: Minimalist engineering visual system for compiled cache staleness verification
colors:
  primary: "#2563eb"
  primary-hover: "#1d4ed8"
  primary-active: "#1e40af"
  primary-focus: "#60a5fa"
  white: "#ffffff"
  neutral-bg: "#090d16"
  neutral-surface: "#0f172a"
  neutral-border: "#1e293b"
  neutral-border-subtle: "#334155"
  text-primary: "#f8fafc"
  text-muted: "#cbd5e1"
  text-subtle: "#94a3b8"
  status-error: "#ef4444"
  status-success: "#2563eb"
typography:
  display-lg:
    fontFamily: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "2.75rem"
    fontWeight: 700
    lineHeight: 1.15
  display:
    fontFamily: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.2
  headline:
    fontFamily: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
  title-sm:
    fontFamily: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.25
  title:
    fontFamily: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  code:
    fontFamily: "'IBM Plex Mono', 'JetBrains Mono', Consolas, monospace"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.3
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  xxl: "64px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.white}"
    rounded: "{rounded.md}"
    padding: "14px 28px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
---

# Design System: StaleByte

## Overview
A hyper-focused, minimal, engineering-grade visual system designed strictly for clarity and usability. It discards decorative clutter, nested cards, gradient fills, and faux-glass aesthetics in favor of clean whitespace, precise typography, a single restrained accent color, and instant cognitive scannability.

## Colors
- **Neutral Background (`#090d16`)**: Pure, deep matte canvas that eliminates eye strain and provides maximum contrast.
- **Neutral Surface (`#0f172a`)**: Subtle, non-intrusive container surface for primary content zones.
- **Hairline Borders (`#1e293b`)**: Crisp 1px geometric divisions defining boundaries without visual heaviness.
- **Primary Accent (`#2563eb`)**: The single focal accent color reserved strictly for the primary interactive action and focus states.
- **Text Primary (`#f8fafc`)**: High-contrast, clean foreground meeting WCAG 2.1 AAA standards (16.5:1).
- **Text Muted (`#cbd5e1`)**: Secondary explanatory copy and labels maintaining >10:1 contrast against surface backgrounds.
- **Text Subtle (`#94a3b8`)**: Captions and meta labels maintaining >6.5:1 contrast against surface backgrounds.

## Typography
- **Headings & Body (`IBM Plex Sans`)**: Distinct industrial Grotesque engineered for technical rigor and readability.
- **Code & Digests (`IBM Plex Mono`)**: Technical monospace face reserved exclusively for real code, filesystem timestamps, and SHA-256 cryptographic digests.

## Layout
- **Mobile-First & Fluid**: Single column layout with generous touch targets (minimum 44px) on small screens, scaling into a balanced 2-column comparison on tablet and desktop (`min-width: 768px`).
- **Whitespace Priority**: Generous vertical margins (`64px` section gaps) ensuring every element has breathing room.
- **Single Dominant Action**: Exactly one high-contrast primary button commands the viewport. Secondary controls are low-profile disclosures.

## Elevation & Depth
- **Completely Flat**: Zero drop shadows, zero gradient overlays. Elevation is represented purely by border boundaries and subtle surface tonal shifts.

## Shapes
- Modest radius (`4px` to `6px`) reflecting clean, utilitarian software engineering. No exaggerated pill shapes or cartoonish borders.

## Components
- **Primary Action Button**: High-contrast, solid fill with subtle hover brightness shift and visible focus ring.
- **Comparison Panels**: Flat, un-nested side-by-side verification panels with clear status headers and code blocks.
- **Provenance Inspector**: Monospace key-value inspector for hashes and filesystem timestamps.

## Do's and Don'ts
- **DO** use abundant whitespace to separate concepts cleanly.
- **DO** preserve high contrast (≥4.5:1) everywhere.
- **DON'T** use gradient backgrounds, gradient text, or glowing halos.
- **DON'T** nest cards inside cards.
- **DON'T** use multiple competing bright accent colors.
