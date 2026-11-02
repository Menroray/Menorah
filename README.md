# Kingsley Glover - Portfolio

A responsive, static portfolio built with semantic HTML, plain CSS, and a
small progressive-enhancement script. There is no framework, build step, or
runtime dependency to install.

## Project files

- `index.html` — page structure and portfolio content; this is the entry point
  used by GitHub Pages.
- `styles.css` — design tokens, components, responsive layout, hover transitions,
  and reduced-motion styles.
- `script.js` — updates the copyright year and repeats content reveal effects as
  you scroll; the page remains usable if JavaScript is disabled.
- The compact footer stays fixed to the bottom of the viewport; page spacing
  keeps the final content reachable above it.
- `assets/` — images used by the page.

## Run locally

Open `index.html` in a browser, or serve this folder with any static file
server. For example, from this directory run `python -m http.server 8000` and
visit `http://localhost:8000`.

Google Fonts are loaded from Google Fonts when a network connection is
available. System font fallbacks are defined in the stylesheet.

## Publish with GitHub Pages

1. Create a GitHub repository and push these project files to its `main` branch.
2. In the repository, open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select the `main` branch and the `/(root)` folder, then save.
5. After GitHub finishes deploying, the Pages URL appears on that settings page.

## Editing guide

- Update copy, links, or page sections in `index.html`.
- Adjust shared colors, typography, spacing, and layout in the `:root` tokens
  near the top of `styles.css`; component-specific styles follow below.
- Keep any new section links and section IDs matched so the navigation works.
- Keep external links that open a new tab paired with
  `rel="noopener noreferrer"`.
- Avoid inline styles and dependencies that require a build system; this keeps
  the site easy to host and maintain.
