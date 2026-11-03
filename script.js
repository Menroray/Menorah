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
    ".hero-copy > *, .hero-content > .portrait-frame, main section:not(.contact-section) .container > *, .skills-grid > *, .project-grid > *, .experience-list > *",
  );

  revealElements.forEach((element) => element.classList.add("reveal"));
  document.documentElement.classList.add("motion-ready");

  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const element = entry.target;

        if (!entry.isIntersecting) {
          return;
        }

        element.classList.add("is-visible");
        revealObserver.unobserve(element);

        // Once revealed, hand transitions back to the component's own
        // hover styles (the reveal rule otherwise overrides them and
        // adds stagger delays to hover effects).
        element.addEventListener(
          "transitionend",
          (event) => {
            if (event.target === element && event.propertyName === "opacity") {
              element.classList.remove("reveal", "is-visible");
            }
          },
          { once: false },
        );
      });
    },
    {
      threshold: 0,
      rootMargin: "0px 0px -32px 0px",
    },
  );

  revealElements.forEach((element) => revealObserver.observe(element));
}