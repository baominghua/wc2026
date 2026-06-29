---
name: Handdrawn Data Lens
colors:
  background: "#07111F"
  surface: "#101B2E"
  surfaceAlt: "#16243A"
  text: "#F7FBFF"
  muted: "#9FB2C8"
  accent: "#66E8FF"
  accent2: "#FFE36E"
  danger: "#FF5D73"
typography:
  family: "Microsoft YaHei"
  displayWeight: 900
  bodyWeight: 650
rounded: "small"
spacing: "grid-locked"
motion: "snappy-handdrawn"
---

# Handdrawn Data Lens

## Overview

This custom theme is for a 16:9 explainer video about building a World Cup prediction model with Codex. It should feel like a technical product walkthrough drawn over a live model dashboard: credible, fast, analytical, but still handmade enough to match the VibeCoding angle.

The viewer should feel they are watching a real project being opened up, not a generic AI promo.

## Colors

- Background uses deep navy black `#07111F`.
- Cards use layered slate surfaces `#101B2E` and `#16243A`.
- Main text is near white `#F7FBFF`.
- Secondary text uses muted blue grey `#9FB2C8`.
- Primary accent is cyan `#66E8FF` for model outputs, selected paths, xG, and probability highlights.
- Secondary accent is yellow `#FFE36E` for warnings, "key takeaway", and champion or outcome moments.
- Risk accent is coral red `#FF5D73`, used sparingly for cold upset/risk signals only.

Do not turn the full video into a purple AI gradient. Use cyan/yellow on dark data panels.

## Typography

- Use Microsoft YaHei for Chinese interface text and JetBrains Mono for code-like fragments.
- Display text is heavy, compact, and short.
- Body labels are semi-bold, never thin.
- Numbers should be large and stable, especially xG, percentages, hit rates, and 32-team / champion outputs.
- Do not use decorative script fonts. Handdrawn feeling comes from annotation strokes, not the typeface.

## Elevation

- Product UI panels use translucent dark glass with crisp 1px cyan or slate borders.
- Data cards can float in shallow 3D perspective, but must stay readable.
- Handdrawn annotation strokes sit above the UI layer and may wiggle slightly.
- Avoid nested cards. If multiple panels appear, lay them out as dashboard tiles.

## Components

- Browser-window UI shots are the main product layer.
- Flow charts, layered stacks, loops, dashboard cards, and comparison tables carry the technical story.
- Handdrawn elements include circles, underline swipes, arrows, check marks, and quick margin notes.
- 3D is limited to floating module cards and data tiles. No realistic football stadium 3D scene is needed.

## Motion

- Module cards SLAM or WHIP in, then settle.
- Handdrawn strokes SCRATCH or DRAW themselves on.
- Probability bars FILL from zero.
- Large numbers COUNT UP.
- Website captures PAN and ZOOM with intentional focus points.
- Use hard cuts for most edits. Use shader transitions only at major section changes.

## Do's

- Keep every frame tied to a website module or model idea.
- Let handdrawn marks explain what matters on screen.
- Use split-screen only when comparing "project structure" with "finished product".
- Make the prediction, review, and qualification sections feel like a product demo, not a slideshow.

## Don'ts

- Do not use betting or wagering wording.
- Do not imply the model guarantees results.
- Do not spend time on empty logo animation.
- Do not show generic football stock footage as the main evidence.
- Do not overload one screen with every metric; zoom into one cluster at a time.
