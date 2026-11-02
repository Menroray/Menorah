# Kingsley Glover — Portfolio

A responsive, static portfolio built with semantic HTML, plain CSS, and a
small progressive-enhancement script. There is no framework, build step, or
runtime dependency to install.

## Project files

- `Main.dc.html` — page structure and portfolio content.
- `styles.css` — design tokens, components, responsive layout, hover transitions,
  and reduced-motion styles.
- `script.js` — updates the copyright year and repeats content reveal effects as
  you scroll; the page remains usable if JavaScript is disabled.
- The compact footer stays fixed to the bottom of the viewport; page spacing
  keeps the final content reachable above it.
- `assets/` — images used by the page.

## Run locally

Open `Main.dc.html` in a browser, or serve this folder with any static file
server. For example, from this directory run `python -m http.server 8000` and
visit `http://localhost:8000/Main.dc.html`.

Google Fonts are loaded from Google Fonts when a network connection is
available. System font fallbacks are defined in the stylesheet.

## Editing guide

- Update copy, links, or page sections in `Main.dc.html`.
- Adjust shared colors, typography, spacing, and layout in the `:root` tokens
  near the top of `styles.css`; component-specific styles follow below.
- Keep any new section links and section IDs matched so the navigation works.
- Keep external links that open a new tab paired with
  `rel="noopener noreferrer"`.
- Avoid inline styles and dependencies that require a build system; this keeps
  the site easy to host and maintain.
