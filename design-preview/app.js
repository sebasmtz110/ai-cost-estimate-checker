(() => {
  const screens = [...document.querySelectorAll(".screen")];
  const tabs = [...document.querySelectorAll(".tab")];
  const goButtons = [...document.querySelectorAll("[data-go]")];

  function showScreen(name) {
    screens.forEach((s) => s.classList.toggle("is-active", s.dataset.screen === name));
    tabs.forEach((t) => t.classList.toggle("is-on", t.dataset.go === name));
    if (name !== "library") closeDetail();
  }

  goButtons.forEach((btn) => {
    btn.addEventListener("click", () => showScreen(btn.dataset.go));
  });

  const restBar = document.getElementById("rest-bar");
  const restClock = document.getElementById("rest-clock");
  let restLeft = 0;
  let restTimer = null;

  function formatRest(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  function stopRest() {
    if (restTimer) clearInterval(restTimer);
    restTimer = null;
    restBar?.classList.remove("is-on");
  }

  function startRest(seconds = 90) {
    restLeft = seconds;
    restClock.textContent = formatRest(restLeft);
    restBar.classList.add("is-on");
    if (restTimer) clearInterval(restTimer);
    restTimer = setInterval(() => {
      restLeft -= 1;
      if (restLeft <= 0) {
        stopRest();
        return;
      }
      restClock.textContent = formatRest(restLeft);
    }, 1000);
  }

  document.querySelectorAll(".set-done").forEach((btn) => {
    btn.addEventListener("click", () => {
      const row = btn.closest("tr");
      const done = btn.classList.toggle("is-done");
      row.classList.toggle("is-done", done);
      if (done) startRest(90);
    });
  });

  document.getElementById("rest-skip")?.addEventListener("click", stopRest);
  document.getElementById("rest-minus")?.addEventListener("click", () => {
    if (!restBar.classList.contains("is-on")) return;
    restLeft = Math.max(0, restLeft - 15);
    restClock.textContent = formatRest(restLeft);
    if (restLeft === 0) stopRest();
  });

  const elapsedEl = document.getElementById("workout-elapsed");
  let elapsed = 12 * 60 + 38;
  setInterval(() => {
    if (!document.getElementById("screen-workout")?.classList.contains("is-active")) return;
    elapsed += 1;
    const h = Math.floor(elapsed / 3600);
    const m = Math.floor((elapsed % 3600) / 60);
    const s = elapsed % 60;
    elapsedEl.textContent = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }, 1000);

  const search = document.getElementById("exercise-search");
  const chips = [...document.querySelectorAll("#muscle-chips .filter")];
  const rows = [...document.querySelectorAll("#exercise-list .ex-row")];
  let muscleFilter = "all";

  function applyLibraryFilter() {
    const q = (search?.value || "").trim().toLowerCase();
    rows.forEach((row) => {
      const muscleOk = muscleFilter === "all" || row.dataset.muscle === muscleFilter;
      const text = `${row.dataset.name} ${row.dataset.equip} ${row.dataset.muscle}`.toLowerCase();
      const searchOk = !q || text.includes(q);
      row.classList.toggle("hidden-by-filter", !(muscleOk && searchOk));
    });
  }

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.classList.remove("is-on"));
      chip.classList.add("is-on");
      muscleFilter = chip.dataset.filter;
      applyLibraryFilter();
    });
  });

  search?.addEventListener("input", applyLibraryFilter);

  const detail = document.getElementById("exercise-detail");
  const detailTitle = document.getElementById("detail-title");
  const detailMuscle = document.getElementById("detail-muscle");
  const detailEquip = document.getElementById("detail-equip");
  const detailImg = document.getElementById("detail-img");

  function closeDetail() {
    detail?.classList.remove("is-open");
    detail?.setAttribute("aria-hidden", "true");
  }

  function openDetail(row) {
    detailTitle.textContent = row.dataset.name;
    detailMuscle.textContent = row.dataset.muscle.replace(/^./, (c) => c.toUpperCase());
    detailEquip.textContent = row.dataset.equip;
    if (detailImg) detailImg.src = row.dataset.img || "";
    detail.classList.add("is-open");
    detail.setAttribute("aria-hidden", "false");
  }

  rows.forEach((row) => row.addEventListener("click", () => openDetail(row)));
  document.getElementById("detail-close")?.addEventListener("click", closeDetail);
})();
