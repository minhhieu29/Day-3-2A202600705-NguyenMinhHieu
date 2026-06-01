const slides = [...document.querySelectorAll(".slide")];
const total = slides.length;
let current = 0;

const progress = document.getElementById("progress");
const counter = document.getElementById("slideCounter");
const btnPrev = document.getElementById("btnPrev");
const btnNext = document.getElementById("btnNext");

function goTo(index) {
  if (index < 0 || index >= total) return;
  slides[current].classList.remove("active");
  current = index;
  slides[current].classList.add("active");
  progress.style.width = `${((current + 1) / total) * 100}%`;
  counter.textContent = `${current + 1} / ${total}`;
}

function next() {
  goTo(current + 1);
}

function prev() {
  goTo(current - 1);
}

btnNext.addEventListener("click", next);
btnPrev.addEventListener("click", prev);

document.addEventListener("keydown", (e) => {
  if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
    e.preventDefault();
    next();
  }
  if (e.key === "ArrowLeft" || e.key === "PageUp") {
    e.preventDefault();
    prev();
  }
  if (e.key === "f" || e.key === "F") {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  }
});

let touchStartX = 0;
document.addEventListener("touchstart", (e) => {
  touchStartX = e.changedTouches[0].screenX;
});
document.addEventListener("touchend", (e) => {
  const dx = e.changedTouches[0].screenX - touchStartX;
  if (Math.abs(dx) < 50) return;
  if (dx < 0) next();
  else prev();
});

goTo(0);
