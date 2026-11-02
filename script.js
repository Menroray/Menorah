"use strict";

const currentYear = document.querySelector("[data-current-year]");

if (currentYear) {
  currentYear.textContent = String(new Date().getFullYear());
}

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

if (
  !reducedMotion.matches &&
  typeof window.IntersectionObserver === "function"
) {
  const revealElements = document.querySelectorAll(
    ".hero-copy > *, .hero-content > .portrait-frame, main section .container > *, .skills-grid > *, .project-grid > *, .experience-list > *, .education-card",
  );

  revealElements.forEach((element) => element.classList.add("reveal"));
  document.documentElement.classList.add("motion-ready");

  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        entry.target.classList.toggle("is-visible", entry.isIntersecting);
      });
    },
    {
      threshold: 0,
      rootMargin: "0px 0px -32px 0px",
    },
  );

  revealElements.forEach((element) => revealObserver.observe(element));
}
