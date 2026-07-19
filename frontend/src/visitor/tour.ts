/** First-visit walkthrough.
 *
 * A cookie ("avatar_tour") marks browsers that have already seen it; new
 * browsers get a six-step spotlight tour of the page controls. Finishing or
 * skipping sets the cookie so the tour never auto-shows again.
 */

import { getCookie, setCookie } from "../lib/cookies";

const TOUR_COOKIE = "avatar_tour";

interface Step {
  selector: string;
  title: string;
  body: string;
}

const STEPS: Step[] = [
  {
    selector: ".name-field",
    title: "Your name",
    body: "Add your name or initials here — your messages get labelled with them, and replies address you personally.",
  },
  {
    selector: ".switch",
    title: "Keep chat",
    body: "Leave this on and the conversation is remembered in this browser — come back later and pick up exactly where you left off.",
  },
  {
    selector: "#resetBtn",
    title: "Reset",
    body: "Starts a completely fresh conversation whenever you want a clean slate.",
  },
  {
    selector: "#themeToggle",
    title: "Dark or light",
    body: "Switch the colour theme any time — your choice is remembered.",
  },
  {
    selector: "#attnBtn",
    title: "Call the real human",
    body: "Press this before sending and that message also pings the real human's phone directly — no special wording needed. It lights up amber, fires once with your message, then switches itself off.",
  },
  {
    selector: ".composer",
    title: "Instant FAQ answers",
    body: "The Qn shortcuts are the numbered FAQ: type Q2 (or any Qn) and the matching frequently-asked question is answered instantly, no AI involved.",
  },
];

export function maybeStartTour(): void {
  if (getCookie(TOUR_COOKIE)) return;
  startTour();
}

export function startTour(): void {
  let index = 0;

  const overlay = document.createElement("div");
  overlay.className = "tour-overlay";
  overlay.innerHTML = `
    <div class="tour-ring" id="tourRing"></div>
    <div class="tour-card card" id="tourCard" role="dialog" aria-modal="true">
      <div class="tour-step eyebrow" id="tourStep"></div>
      <h2 id="tourTitle"></h2>
      <p id="tourBody"></p>
      <div class="tour-actions">
        <button class="btn btn--ghost btn--sm" id="tourSkip">Skip tour</button>
        <button class="btn btn--primary btn--sm" id="tourNext">Next</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  const ring = overlay.querySelector("#tourRing") as HTMLElement;
  const card = overlay.querySelector("#tourCard") as HTMLElement;
  const stepLabel = overlay.querySelector("#tourStep") as HTMLElement;
  const title = overlay.querySelector("#tourTitle") as HTMLElement;
  const body = overlay.querySelector("#tourBody") as HTMLElement;
  const nextBtn = overlay.querySelector("#tourNext") as HTMLButtonElement;

  const finish = () => {
    setCookie(TOUR_COOKIE, "1");
    overlay.remove();
    window.removeEventListener("resize", position);
    (document.getElementById("composerInput") as HTMLTextAreaElement)?.focus({
      preventScroll: true,
    });
  };

  const visibleSteps = STEPS.filter((step) => {
    const el = document.querySelector<HTMLElement>(step.selector);
    return el && el.offsetParent !== null;
  });
  if (visibleSteps.length === 0) {
    finish();
    return;
  }

  const position = () => {
    const step = visibleSteps[index];
    const target = document.querySelector<HTMLElement>(step.selector);
    if (!target) return;
    const rect = target.getBoundingClientRect();
    const pad = 6;
    ring.style.top = `${rect.top - pad}px`;
    ring.style.left = `${rect.left - pad}px`;
    ring.style.width = `${rect.width + pad * 2}px`;
    ring.style.height = `${rect.height + pad * 2}px`;

    // Card below the target when there's room, otherwise above; clamped to
    // the viewport. On narrow screens it sits centred near the bottom.
    const cardRect = card.getBoundingClientRect();
    if (window.innerWidth < 640) {
      card.style.left = "50%";
      card.style.transform = "translateX(-50%)";
      card.style.top = "auto";
      card.style.bottom = "16px";
      return;
    }
    card.style.transform = "";
    card.style.bottom = "auto";
    let top = rect.bottom + 14;
    if (top + cardRect.height > window.innerHeight - 16) {
      top = Math.max(16, rect.top - cardRect.height - 14);
    }
    let left = Math.min(
      Math.max(16, rect.left),
      window.innerWidth - cardRect.width - 16,
    );
    card.style.top = `${top}px`;
    card.style.left = `${left}px`;
  };

  const render = () => {
    const step = visibleSteps[index];
    stepLabel.textContent = `Step ${index + 1} of ${visibleSteps.length}`;
    title.textContent = step.title;
    body.textContent = step.body;
    nextBtn.textContent = index === visibleSteps.length - 1 ? "Done" : "Next";
    position();
  };

  nextBtn.addEventListener("click", () => {
    if (index >= visibleSteps.length - 1) {
      finish();
    } else {
      index += 1;
      render();
    }
  });
  (overlay.querySelector("#tourSkip") as HTMLElement).addEventListener(
    "click",
    finish,
  );
  window.addEventListener("resize", position);

  render();
  // Re-position once fonts/layout settle
  setTimeout(position, 150);
}
