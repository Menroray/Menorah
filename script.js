"use strict";

const currentYear = document.querySelector("[data-current-year]");

if (currentYear) {
  currentYear.textContent = String(new Date().getFullYear());
}

const revealGroups = [
  { selector: ".hero-copy > *", effect: "rise" },
  { selector: ".hero-content > .portrait-frame", effect: "portrait" },
  {
    selector: "#about .container > .eyebrow, #about .about-copy > p",
    effect: "rise",
  },
  { selector: "#about .container > .section-title", effect: "clip" },
  { selector: "#about .education-card", effect: "from-right" },
  { selector: "#skills .container > .eyebrow", effect: "rise" },
  { selector: "#skills .container > .section-title", effect: "focus" },
  { selector: ".skills-grid > *", effect: "pop" },
  { selector: "#projects .container > .eyebrow", effect: "rise" },
  { selector: "#projects .container > .section-title", effect: "scale" },
  { selector: "#projects .featured-project", effect: "sweep" },
  { selector: ".project-grid > *", effect: "tilt" },
  { selector: "#experience .container > .eyebrow", effect: "rise" },
  { selector: "#experience .container > .section-title", effect: "timeline" },
  { selector: ".experience-list > *", effect: "from-left" },
  { selector: "#contact-title", effect: "contact-title" },
  { selector: "#contact .contact-copy", effect: "from-left" },
  { selector: "#contact .contact-card", effect: "from-right" },
];
const revealElements = [];
let revealObserver;

function enableRevealAnimations() {
  if (typeof window.IntersectionObserver !== "function") {
    return;
  }

  revealGroups.forEach(({ selector, effect }) => {
    document.querySelectorAll(selector).forEach((element) => {
      if (element.classList.contains("reveal")) {
        return;
      }

      element.classList.add("reveal", `reveal-${effect}`);
      revealElements.push({ element, effect });
    });
  });

  if (revealElements.length === 0) {
    return;
  }

  document.documentElement.classList.add("motion-ready");
  revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(({ target, isIntersecting }) => {
        target.classList.toggle("is-visible", isIntersecting);
      });
    },
    { threshold: 0.01, rootMargin: "0px 0px -32px 0px" },
  );

  revealElements.forEach(({ element }) => revealObserver.observe(element));
}

enableRevealAnimations();