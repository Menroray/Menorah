# Kingsley Glover - Portfolio

A responsive static portfolio built with semantic HTML, CSS, and a small
progressive-enhancement script. It has no framework, build step, or runtime
dependency to install.

## Project files

| File | Purpose |
| --- | --- |
| `index.html` | Page content, section structure, navigation, and contact links |
| `styles.css` | Design tokens, components, responsive layout, and animations |
| `script.js` | Copyright year and optional scroll-reveal animations |
| `assets/` | Images used by the page |

The navigation stays fixed at the top, and the footer stays fixed at the
bottom. Spacing keeps the page content reachable around both.

## Quick editing guide

- **Text, contact details, and links:** edit the matching section in
  `index.html`. The page is ordered from the hero to About, Skills, Projects,
  Experience, and Contact.
- **Add or remove a section:** update its `<section id="...">` and any
  navigation link that points to it. Keep IDs unique.
- **Add a card:** copy a neighboring card's complete HTML element, then replace
  its text and links.
- **Change the portrait:** update the image `src` and its descriptive `alt`
  text in `index.html`.
- **Change colors, fonts, or spacing:** edit the named CSS variables in the
  `:root` block at the top of `styles.css`. Component-specific rules follow.
- **Change scroll animations:** edit the selector/effect pairs in
  `revealGroups` in `script.js`. Reveals replay each time an element leaves and
  re-enters the viewport. The system's reduced-motion preference is respected
  and can be changed while the page is open. The page still works without
  JavaScript.
- **Change the browser security policy:** edit the Content Security Policy
  (`Content-Security-Policy`) meta tag in the `<head>` of `index.html`. When
  adding an external resource, allow only the specific origin and resource
  type it needs; avoid broad sources such as `*` or `unsafe-inline`.

External links that open a new tab should use HTTPS and keep
`rel="noopener noreferrer"`.

## Security notes

- The Content Security Policy only allows this site's own scripts and assets,
  plus Google Fonts for styles and font files. Keep scripts and styles in their
  separate files rather than adding inline code.
- This is a public static website: anything placed in its HTML, CSS, JavaScript,
  or assets can be read by visitors. Never put passwords, API keys, private
  tokens, or other secrets here. Features that require secrets need a secured
  server-side service.
- The policy is delivered as an HTML meta tag. Hosting-level HTTP security
  headers can provide additional protections; configure those with the hosting
  provider if available.

## Run locally

Open `index.html` in a browser, or serve this folder with a static file server.
For example, from this directory run `python -m http.server 8000` and visit
`http://localhost:8000`.

Google Fonts are loaded from Google when a network connection is available.
System font fallbacks are defined in the stylesheet.

## Publish with GitHub Pages

1. Create a GitHub repository and push these project files to its `main` branch.
2. In the repository, open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select the `main` branch and the `/(root)` folder, then save.
5. After GitHub finishes deploying, the Pages URL appears on that settings page.
