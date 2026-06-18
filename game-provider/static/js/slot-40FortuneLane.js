
let cfg = null;

const state = {
  balance: 1000,
  freeSpins: 0,
  freeSpinBet: 10,
  spinning: false,
  turbo: false,
  autoFreeSpinsRunning: false,
  lastData: null,
  previewData: null,
  reelW: 210,
  rowH: 150,
  gap: 5,
  canSkip: false,
  skipResolve: null,
  resizeTimer: null,
};

const soundState = {
  ctx: null,
  enabled: true,
};

function $(id) {
  return document.getElementById(id);
}

function money(value) {
  return Number(value || 0).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function nextFrame() {
  return new Promise(resolve => requestAnimationFrame(resolve));
}

/* ---------- SOUND ---------- */

function initAudio() {
  if (!soundState.enabled) return null;

  if (!soundState.ctx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;

    if (!AudioContext) {
      soundState.enabled = false;
      return null;
    }

    soundState.ctx = new AudioContext();
  }

  if (soundState.ctx.state === "suspended") {
    soundState.ctx.resume();
  }

  return soundState.ctx;
}

function playTone({
  frequency = 440,
  duration = 0.08,
  type = "sine",
  volume = 0.035,
  slideTo = null,
}) {
  const ctx = initAudio();
  if (!ctx) return;

  const now = ctx.currentTime;
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();

  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, now);

  if (slideTo) {
    oscillator.frequency.exponentialRampToValueAtTime(slideTo, now + duration);
  }

  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(volume, now + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

  oscillator.connect(gain);
  gain.connect(ctx.destination);

  oscillator.start(now);
  oscillator.stop(now + duration + 0.03);
}

function playSpinStartSound() {
  playTone({
    frequency: 180,
    slideTo: 330,
    duration: 0.16,
    type: "sawtooth",
    volume: 0.026,
  });
}

function playStopSound(col = 0) {
  playTone({
    frequency: 260 + col * 42,
    duration: 0.06,
    type: "square",
    volume: 0.025,
  });
}

function playWinSound(amount = 0) {
  const big = Number(amount) >= 100;
  const notes = big ? [420, 560, 760, 980] : [360, 460, 620];

  notes.forEach((frequency, index) => {
    setTimeout(() => {
      playTone({
        frequency,
        duration: big ? 0.15 : 0.11,
        type: "triangle",
        volume: big ? 0.046 : 0.04,
      });
    }, index * 95);
  });
}

function playJackpotSound() {
  [520, 660, 780, 1040, 1320].forEach((frequency, index) => {
    setTimeout(() => {
      playTone({
        frequency,
        duration: 0.16,
        type: "triangle",
        volume: 0.05,
      });
    }, index * 95);
  });
}

function playNoWinSound() {
  playTone({
    frequency: 190,
    slideTo: 120,
    duration: 0.16,
    type: "sine",
    volume: 0.022,
  });
}

function playScatterBaitSound() {
  playTone({
    frequency: 520,
    slideTo: 390,
    duration: 0.12,
    type: "triangle",
    volume: 0.032,
  });

  setTimeout(() => {
    playTone({
      frequency: 640,
      slideTo: 510,
      duration: 0.12,
      type: "triangle",
      volume: 0.03,
    });
  }, 110);
}

/* ---------- BASIC HELPERS ---------- */

function isPhone() {
  return window.innerWidth <= 700;
}

function getRows() {
  return Number(cfg?.rows || 4);
}

function getCols() {
  return Number(cfg?.cols || 5);
}

function getScatterId() {
  return cfg?.scatter || cfg?.SCATTER || "SCATTER";
}

function getWildId() {
  return cfg?.wild || cfg?.WILD || "WILD";
}

function getSymbolIds() {
  if (Array.isArray(cfg?.symbolIds)) return cfg.symbolIds;
  if (Array.isArray(cfg?.symbols)) return cfg.symbols;
  if (cfg?.symbolMeta) return Object.keys(cfg.symbolMeta);
  if (cfg?.symbols && typeof cfg.symbols === "object") return Object.keys(cfg.symbols);

  return [
    "CHERRY",
    "LEMON",
    "ORANGE",
    "GRAPES",
    "STRAWBERRY",
    "WATERMELON",
    "PINEAPPLE",
    "PEACH",
    "WILD",
    "SCATTER",
  ];
}

function getSymbolMeta(symbol) {
  const meta =
    cfg?.symbolMeta?.[symbol] ||
    cfg?.symbols?.[symbol] ||
    {};

  return {
    label: meta.label || symbol,
    asset: meta.asset || "",
  };
}

/* ---------- UI STATE ---------- */

function updateBalance(value) {
  state.balance = Number(value || 0);

  const el = $("balance");
  if (el) {
    el.textContent = money(state.balance);
  }

  updateBuyBonusCost();
}

function updateFreeSpins(count, bet) {
  state.freeSpins = Number(count || 0);

  if (bet !== undefined && bet !== null) {
    state.freeSpinBet = Number(bet || 10);
  }

  const panel = $("freeSpinsPanel");

  if (panel) {
    if (state.freeSpins > 0) {
      panel.classList.remove("hidden");
      panel.textContent = `${state.freeSpins} Free Spins · $${money(state.freeSpinBet)} Bet`;
    } else {
      panel.classList.add("hidden");
      panel.textContent = "";
    }
  }

  updateSpinButtonText();
  updateBuyBonusCost();
}

function updateSpinButtonText() {
  const spinBtn = $("spinBtn");
  if (!spinBtn || state.spinning) return;

  spinBtn.textContent = state.freeSpins > 0 ? "Free Spin" : "Spin";
}

function updateJackpots(pools) {
  if (!pools) return;

  const grand = $("jackpotGrand");
  const major = $("jackpotMajor");
  const minor = $("jackpotMinor");
  const mini = $("jackpotMini");

  if (grand) grand.textContent = money(pools.GRAND ?? pools.grand ?? 10000);
  if (major) major.textContent = money(pools.MAJOR ?? pools.major ?? 1500);
  if (minor) minor.textContent = money(pools.MINOR ?? pools.minor ?? 250);
  if (mini) mini.textContent = money(pools.MINI ?? pools.mini ?? 50);
}

function setResultBanner(message, type = "") {
  const banner = $("resultBanner");
  if (!banner) return;

  banner.className = `result-banner ${type}`;
  banner.innerHTML = message;
  banner.classList.remove("hidden");
}

function clearResultBanner() {
  const banner = $("resultBanner");
  if (!banner) return;

  banner.classList.add("hidden");
  banner.innerHTML = "";
}

function getSelectedBet() {
  const betInput = $("bet");
  return Math.max(1, parseInt(betInput?.value || "1", 10));
}

function getBuyBonusCost() {
  return getSelectedBet() * 100;
}

function updateBuyBonusCost() {
  const costEl = $("buyBonusCost");
  const btn = $("buyBonusBtn");
  const cost = getBuyBonusCost();

  if (costEl) {
    costEl.textContent = money(cost);
  }

  if (btn) {
    btn.disabled = state.spinning || state.autoFreeSpinsRunning || state.balance < cost;
  }
}

/* ---------- RESPONSIVE SLOT SIZE ---------- */

function getOuterHeight(el) {
  if (!el) return 0;

  const style = window.getComputedStyle(el);

  if (style.display === "none" || style.visibility === "hidden") {
    return 0;
  }

  return (
    el.offsetHeight +
    parseFloat(style.marginTop || 0) +
    parseFloat(style.marginBottom || 0)
  );
}

function syncResponsiveSlotSize() {
  if (!cfg) return;

  const rows = getRows();
  const cols = getCols();

  const stage = document.querySelector(".slot-stage");
  const jackpotBar = document.querySelector(".jackpot-bar");
  const bottomHud = document.querySelector(".bottom-hud");
  const resultBanner = document.querySelector(".result-banner:not(.hidden)");
  const lineResults = document.querySelector(".line-results");

  const stageStyle = stage ? window.getComputedStyle(stage) : null;

  const stagePaddingX = stageStyle
    ? parseFloat(stageStyle.paddingLeft || 0) + parseFloat(stageStyle.paddingRight || 0)
    : 0;

  const stagePaddingY = stageStyle
    ? parseFloat(stageStyle.paddingTop || 0) + parseFloat(stageStyle.paddingBottom || 0)
    : 0;

  const stageWidth = stage ? stage.clientWidth : window.innerWidth;
  const stageHeight = stage ? stage.clientHeight : window.innerHeight;

  const usedHeight =
    stagePaddingY +
    getOuterHeight(jackpotBar) +
    getOuterHeight(bottomHud) +
    getOuterHeight(resultBanner) +
    getOuterHeight(lineResults);

  const availableWidth = Math.max(
    120,
    Math.min(window.innerWidth - 8, stageWidth - stagePaddingX - 8)
  );

  const availableHeight = Math.max(
    120,
    stageHeight - usedHeight - 8
  );

  const gap = isPhone() ? 3 : 5;

  const maxReelWByWidth =
    (availableWidth - gap * (cols - 1)) / cols;

  const maxReelWByHeight =
    (availableHeight / rows) / 0.72;

  const minReelW = isPhone() ? 34 : 42;

  const reelW = Math.floor(
    Math.max(
      minReelW,
      Math.min(
        210,
        maxReelWByWidth,
        maxReelWByHeight
      )
    )
  );

  const rowH = Math.floor(
    Math.max(
      28,
      Math.min(
        150,
        reelW * 0.72,
        availableHeight / rows
      )
    )
  );

  state.reelW = reelW;
  state.rowH = rowH;
  state.gap = gap;

  document.documentElement.style.setProperty("--reel-w", `${reelW}px`);
  document.documentElement.style.setProperty("--row-h", `${rowH}px`);
  document.documentElement.style.setProperty("--gap", `${gap}px`);

  const boardW = cols * reelW + (cols - 1) * gap;
  const boardH = rows * rowH;

  const board = $("board");
  const reels = $("reels");
  const overlay = $("lineOverlay");

  if (board) {
    board.style.width = `${boardW}px`;
    board.style.height = `${boardH}px`;
    board.style.minWidth = "0";
  }

  if (reels) {
    reels.style.width = `${boardW}px`;
    reels.style.height = `${boardH}px`;
    reels.style.minWidth = "0";
    reels.style.gridTemplateColumns = `repeat(${cols}, ${reelW}px)`;
    reels.style.gap = `${gap}px`;
  }

  if (overlay) {
    overlay.setAttribute("width", boardW);
    overlay.setAttribute("height", boardH);
    overlay.setAttribute("viewBox", `0 0 ${boardW} ${boardH}`);
  }
}

/* ---------- DATA HELPERS ---------- */

function getGridSymbol(grid, row, col) {
  if (!grid) return null;

  if (Array.isArray(grid[row]) && grid[row][col] !== undefined) {
    return grid[row][col];
  }

  if (Array.isArray(grid[col]) && grid[col][row] !== undefined) {
    return grid[col][row];
  }

  return null;
}

function makeFallbackReel(length = 120) {
  const ids = getSymbolIds();
  const reel = [];

  for (let i = 0; i < length; i++) {
    reel.push(ids[i % ids.length]);
  }

  return reel;
}

function getSpinDepth(col) {
  const base = state.turbo ? 30 : isPhone() ? 42 : 58;
  const step = state.turbo ? 7 : isPhone() ? 9 : 14;

  return base + col * step;
}

function getCellMultiplier(data, row, col) {
  const sources = [
    data?.wildMultipliers,
    data?.wild_multipliers,
    data?.multipliers,
    data?.multiplierGrid,
    data?.multiplier_grid,
  ];

  for (const source of sources) {
    if (!source) continue;

    if (Array.isArray(source)) {
      for (const item of source) {
        if (Array.isArray(item)) {
          const itemRow = Number(item[0]);
          const itemCol = Number(item[1]);
          const multiplier = Number(item[2]);

          if (itemRow === row && itemCol === col && multiplier > 1) {
            return multiplier;
          }
        } else if (typeof item === "object") {
          const itemRow = Number(item.row ?? item.r);
          const itemCol = Number(item.col ?? item.c);
          const multiplier = Number(item.multiplier ?? item.mult ?? item.value);

          if (itemRow === row && itemCol === col && multiplier > 1) {
            return multiplier;
          }
        }
      }
    }

    if (typeof source === "object") {
      const keys = [
        `${row}:${col}`,
        `${row}-${col}`,
        `${row},${col}`,
        `${col}:${row}`,
        `${col}-${row}`,
        `${col},${row}`,
      ];

      for (const key of keys) {
        const multiplier = Number(source[key]);

        if (multiplier > 1) {
          return multiplier;
        }
      }

      if (Array.isArray(source[row]) && Number(source[row][col]) > 1) {
        return Number(source[row][col]);
      }
    }
  }

  return null;
}

function normalizeSpinData(data = {}) {
  const rows = getRows();
  const cols = getCols();

  const stops = Array.isArray(data.stops)
    ? data.stops.map(v => Number(v || 0))
    : Array.from({ length: cols }, () => 40);

  let reels = Array.isArray(data.reels)
    ? data.reels
    : Array.isArray(data.strips)
      ? data.strips
      : null;

  if (!reels) {
    reels = Array.from({ length: cols }, () => makeFallbackReel(120));
  }

  reels = reels.map((reel, col) => {
    const base = Array.isArray(reel) && reel.length ? reel : makeFallbackReel(120);

    const neededLength = Math.max(
      stops[col] + getSpinDepth(col) + rows + 12,
      rows + getSpinDepth(col) + 12
    );

    const expanded = [];

    for (let i = 0; i < neededLength; i++) {
      expanded.push(base[i % base.length]);
    }

    for (let row = 0; row < rows; row++) {
      const symbol = getGridSymbol(data.grid, row, col);
      if (symbol) {
        expanded[stops[col] + row] = symbol;
      }
    }

    return expanded;
  });

  return {
    ...data,
    stops,
    reels,
  };
}

/* ---------- RENDERING ---------- */

function createSymbolCell(symbol, col, stripIndex, multiplier = null) {
  const cell = document.createElement("div");

  cell.className = "symbol";
  cell.dataset.symbol = symbol;
  cell.dataset.col = String(col);
  cell.dataset.stripIndex = String(stripIndex);

  const meta = getSymbolMeta(symbol);

  if (meta.asset) {
    const img = document.createElement("img");
    img.src = meta.asset;
    img.alt = meta.label;
    img.loading = "eager";
    img.decoding = "async";
    cell.appendChild(img);
  } else {
    const fallback = document.createElement("div");
    fallback.className = "symbol-text";
    fallback.textContent = symbol;
    cell.appendChild(fallback);
  }

  if (symbol === getWildId()) {
    cell.classList.add("wild-symbol");

    if (Number(multiplier) > 1) {
      const badge = document.createElement("span");
      badge.className = "wild-multiplier";
      badge.textContent = `x${multiplier}`;
      cell.appendChild(badge);
    }
  }

  if (symbol === getScatterId()) {
    cell.classList.add("scatter-symbol");
  }

  return cell;
}

function renderSpinStrips(rawData) {
  if (!cfg) return rawData;

  const data = normalizeSpinData(rawData);
  const reelsRoot = $("reels");

  if (!reelsRoot) return data;

  syncResponsiveSlotSize();

  const fragment = document.createDocumentFragment();

  for (let col = 0; col < getCols(); col++) {
    const reel = document.createElement("div");
    reel.className = "reel";
    reel.dataset.col = String(col);

    const strip = document.createElement("div");
    strip.className = "strip";

    const stripFragment = document.createDocumentFragment();
    const symbols = data.reels[col] || makeFallbackReel(120);

    symbols.forEach((symbol, stripIndex) => {
      const visibleRow = stripIndex - Number(data.stops[col] || 0);

      const multiplier =
        visibleRow >= 0 && visibleRow < getRows()
          ? getCellMultiplier(data, visibleRow, col)
          : null;

      stripFragment.appendChild(
        createSymbolCell(symbol, col, stripIndex, multiplier)
      );
    });

    strip.appendChild(stripFragment);
    reel.appendChild(strip);
    fragment.appendChild(reel);
  }

  reelsRoot.replaceChildren(fragment);

  return data;
}

function setReelsToStops(data) {
  const strips = Array.from(document.querySelectorAll(".strip"));

  strips.forEach((strip, col) => {
    const stop = Number(data.stops?.[col] || 0);
    strip.style.transition = "none";
    strip.style.transform = `translate3d(0, ${-stop * state.rowH}px, 0)`;
  });
}

/* ---------- SCATTER BAIT ---------- */

function countScattersInColumn(data, col) {
  const scatter = getScatterId();
  let count = 0;

  for (let row = 0; row < getRows(); row++) {
    const fromGrid = getGridSymbol(data.grid, row, col);
    const fromReel = data.reels?.[col]?.[Number(data.stops?.[col] || 0) + row];
    const symbol = fromGrid || fromReel;

    if (symbol === scatter) {
      count += 1;
    }
  }

  return count;
}

function getScatterBaitColumns(data) {
  const baitColumns = new Set();
  let scatterCountBefore = 0;

  for (let col = 0; col < getCols(); col++) {
    if (scatterCountBefore >= 2) {
      baitColumns.add(col);
    }

    scatterCountBefore += countScattersInColumn(data, col);
  }

  return baitColumns;
}

/* ---------- CONTROLS ---------- */

function requestSkip() {
  if (state.canSkip && typeof state.skipResolve === "function") {
    state.skipResolve();
  }
}

function enableSkipButton() {
  const btn = $("spinBtn");
  if (!btn) return;

  btn.disabled = false;
  btn.textContent = "Skip";
}

function setControlsEnabled(enabled) {
  const spinBtn = $("spinBtn");
  const bet = $("bet");
  const turbo = $("turboBtn");
  const max = $("maxBtn");
  const buy = $("buyBonusBtn");

  if (spinBtn) {
    spinBtn.disabled = !enabled;
    spinBtn.textContent = enabled
      ? state.freeSpins > 0
        ? "Free Spin"
        : "Spin"
      : "Loading...";
  }

  if (bet) bet.disabled = !enabled || state.freeSpins > 0 || state.autoFreeSpinsRunning;
  if (turbo) turbo.disabled = !enabled;
  if (max) max.disabled = !enabled || state.freeSpins > 0 || state.autoFreeSpinsRunning;

  if (buy) {
    buy.disabled =
      !enabled ||
      state.freeSpins > 0 ||
      state.autoFreeSpinsRunning ||
      state.balance < getBuyBonusCost();
  }
}

/* ---------- SLOT ANIMATION ---------- */

async function animateToStops(data) {
  const strips = Array.from(document.querySelectorAll(".strip"));
  const reels = Array.from(document.querySelectorAll(".reel"));

  const baitColumns = getScatterBaitColumns(data);

  const baseDuration = state.turbo
    ? 700
    : isPhone()
      ? 1250
      : 1850;

  const step = state.turbo
    ? 90
    : isPhone()
      ? 150
      : 260;

  const baitExtra = state.turbo
    ? 450
    : isPhone()
      ? 900
      : 1450;

  const timers = [];
  const animations = [];
  const targets = [];

  state.canSkip = false;
  state.skipResolve = null;

  strips.forEach((strip, col) => {
    const startIndex = Number(data.stops[col] || 0) + getSpinDepth(col);
    const startY = -startIndex * state.rowH;
    const targetY = -Number(data.stops[col] || 0) * state.rowH;

    targets[col] = targetY;

    strip.style.transition = "none";
    strip.style.transform = `translate3d(0, ${startY}px, 0)`;

    if (reels[col]) {
      reels[col].classList.add("spinning");
      reels[col].classList.remove("landed", "scatter-bait");
    }
  });

  await nextFrame();
  await nextFrame();

  return new Promise(resolve => {
    let finished = false;
    let finishedCount = 0;

    function cleanFinish() {
      state.canSkip = false;
      state.skipResolve = null;
      resolve();
    }

    function finishNow() {
      if (finished) return;

      finished = true;

      timers.forEach(timer => clearTimeout(timer));

      animations.forEach(animation => {
        try {
          animation.cancel();
        } catch (_) {}
      });

      strips.forEach((strip, col) => {
        strip.style.transition = "none";
        strip.style.transform = `translate3d(0, ${targets[col]}px, 0)`;

        if (reels[col]) {
          reels[col].classList.remove("spinning", "scatter-bait");
          reels[col].classList.add("landed");
        }

        playStopSound(col);
      });

      cleanFinish();
    }

    state.canSkip = true;
    state.skipResolve = finishNow;
    enableSkipButton();

    strips.forEach((strip, col) => {
      const startIndex = Number(data.stops[col] || 0) + getSpinDepth(col);
      const startY = -startIndex * state.rowH;
      const targetY = targets[col];
      const isBaitReel = baitColumns.has(col);

      const overshoot = Math.min(
        isBaitReel ? 34 : 24,
        state.rowH * (isBaitReel ? 0.18 : 0.13)
      );

      const recoil = Math.min(
        isBaitReel ? 12 : 8,
        state.rowH * (isBaitReel ? 0.07 : 0.045)
      );

      const duration = baseDuration + col * step + (isBaitReel ? baitExtra : 0);

      if (isBaitReel && reels[col]) {
        const baitStart = Math.max(180, baseDuration + Math.max(0, col - 1) * step - 160);

        timers.push(setTimeout(() => {
          if (finished) return;

          reels[col].classList.add("scatter-bait");
          playScatterBaitSound();
        }, baitStart));
      }

      const keyframes = isBaitReel
        ? [
            {
              transform: `translate3d(0, ${startY}px, 0)`,
              offset: 0,
              easing: "linear",
            },
            {
              transform: `translate3d(0, ${targetY + state.rowH * 2.4}px, 0)`,
              offset: 0.56,
              easing: "linear",
            },
            {
              transform: `translate3d(0, ${targetY + state.rowH * 1.25}px, 0)`,
              offset: 0.70,
              easing: "cubic-bezier(.12,.72,.18,1)",
            },
            {
              transform: `translate3d(0, ${targetY + state.rowH * 0.55}px, 0)`,
              offset: 0.82,
              easing: "ease-in-out",
            },
            {
              transform: `translate3d(0, ${targetY + overshoot}px, 0)`,
              offset: 0.93,
              easing: "cubic-bezier(.08,.82,.13,1)",
            },
            {
              transform: `translate3d(0, ${targetY - recoil}px, 0)`,
              offset: 0.975,
              easing: "ease-out",
            },
            {
              transform: `translate3d(0, ${targetY}px, 0)`,
              offset: 1,
              easing: "ease-out",
            },
          ]
        : [
            {
              transform: `translate3d(0, ${startY}px, 0)`,
              offset: 0,
              easing: "linear",
            },
            {
              transform: `translate3d(0, ${targetY + overshoot}px, 0)`,
              offset: 0.86,
              easing: "cubic-bezier(.08,.82,.13,1)",
            },
            {
              transform: `translate3d(0, ${targetY - recoil}px, 0)`,
              offset: 0.94,
              easing: "ease-out",
            },
            {
              transform: `translate3d(0, ${targetY}px, 0)`,
              offset: 1,
              easing: "ease-out",
            },
          ];

      const animation = strip.animate(keyframes, {
        duration,
        fill: "forwards",
      });

      animations.push(animation);

      animation.onfinish = () => {
        if (finished) return;

        strip.style.transition = "none";
        strip.style.transform = `translate3d(0, ${targetY}px, 0)`;

        if (reels[col]) {
          reels[col].classList.remove("spinning", "scatter-bait");
          reels[col].classList.add("landed");
        }

        playStopSound(col);

        finishedCount += 1;

        if (finishedCount >= strips.length) {
          finished = true;
          timers.forEach(timer => clearTimeout(timer));
          cleanFinish();
        }
      };
    });

    const longestDuration =
      baseDuration +
      (getCols() - 1) * step +
      baitExtra +
      700;

    timers.push(setTimeout(finishNow, longestDuration));
  });
}

/* ---------- WIN DISPLAY ---------- */

function clearHighlights() {
  document
    .querySelectorAll(".symbol.win, .symbol.scatter-win, .symbol.drop-land")
    .forEach(cell => {
      cell.classList.remove("win", "scatter-win", "drop-land");
    });

  const overlay = $("lineOverlay");
  if (overlay) {
    overlay.innerHTML = "";
  }
}

function highlightWinningSymbols(data) {
  clearHighlights();

  const cells = data.winningCells || data.winning_cells || [];
  const seen = new Set();

  cells.forEach(cellData => {
    const row = Array.isArray(cellData) ? Number(cellData[0]) : Number(cellData.row);
    const col = Array.isArray(cellData) ? Number(cellData[1]) : Number(cellData.col);

    if (Number.isNaN(row) || Number.isNaN(col)) return;

    const key = `${row}-${col}`;
    if (seen.has(key)) return;
    seen.add(key);

    const visibleStripIndex = Number(data.stops[col] || 0) + row;
    const selector = `.symbol[data-col="${col}"][data-strip-index="${visibleStripIndex}"]`;
    const cell = document.querySelector(selector);

    if (!cell) return;

    if (cell.dataset.symbol === getScatterId()) {
      cell.classList.add("scatter-win");
    } else {
      cell.classList.add("win");
    }
  });
}

function cellCenter(row, col) {
  return {
    x: col * (state.reelW + state.gap) + state.reelW / 2,
    y: row * state.rowH + state.rowH / 2,
  };
}

function getWinLines(data) {
  return (
    data.lineWins ||
    data.line_wins ||
    data.lines ||
    data.wins ||
    []
  );
}

function drawWinLines(data) {
  const overlay = $("lineOverlay");
  if (!overlay) return;

  overlay.innerHTML = "";

  if (isPhone()) return;

  const winLines = getWinLines(data);
  if (!Array.isArray(winLines)) return;

  winLines.slice(0, 8).forEach((winLine, index) => {
    const cells =
      winLine.cells ||
      winLine.matchedCells ||
      winLine.matched_cells ||
      [];

    if (!Array.isArray(cells) || cells.length < 2) return;

    const points = cells
      .map(cell => {
        const row = Array.isArray(cell) ? Number(cell[0]) : Number(cell.row);
        const col = Array.isArray(cell) ? Number(cell[1]) : Number(cell.col);

        if (Number.isNaN(row) || Number.isNaN(col)) return null;

        return cellCenter(row, col);
      })
      .filter(Boolean);

    if (points.length < 2) return;

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");

    const d = points
      .map((point, i) => `${i === 0 ? "M" : "L"} ${point.x} ${point.y}`)
      .join(" ");

    path.setAttribute("d", d);
    path.setAttribute("class", "active-win-path");
    path.style.animationDelay = `${index * 80}ms`;

    overlay.appendChild(path);
  });
}

function renderWinList(data) {
  const lineResults = $("lineResults");
  if (!lineResults) return;

  const winLines = getWinLines(data);
  const scatterWin = Number(data.scatterWin || data.scatter_win || 0);
  const totalWin = Number(data.win || data.totalWin || 0) + Number(data.jackpotWin || data.jackpot_win || 0);

  if (!winLines.length && !scatterWin && totalWin <= 0) {
    lineResults.innerHTML = "";
    return;
  }

  const rows = [];

  winLines.slice(0, isPhone() ? 8 : 20).forEach(win => {
    const symbol = win.symbol || win.matchSymbol || win.match_symbol || "Line";
    const count = win.count || win.length || "";
    const amount = win.win || win.amount || 0;

    rows.push(`
      <div class="win-row">
        <span>${symbol}${count ? ` × ${count}` : ""}</span>
        <strong>$${money(amount)}</strong>
      </div>
    `);
  });

  if (scatterWin > 0) {
    rows.push(`
      <div class="win-row">
        <span>Scatter Win</span>
        <strong>$${money(scatterWin)}</strong>
      </div>
    `);
  }

  lineResults.innerHTML = `
    <div class="win-list">
      ${rows.join("")}
    </div>
  `;
}

function showWinOverlay(amount) {
  const overlay = $("winOverlay");
  if (!overlay) return;

  const title = overlay.querySelector(".win-overlay-title");
  const amountEl = overlay.querySelector(".win-overlay-amount");

  if (title) {
    title.textContent = Number(amount) >= 500 ? "BIG WIN" : "WIN";
  }

  if (amountEl) {
    amountEl.textContent = `$${money(amount)}`;
  }

  overlay.classList.toggle("extreme", Number(amount) >= 500);
  overlay.classList.remove("hidden");

  setTimeout(() => {
    overlay.classList.add("hidden");
  }, state.turbo ? 650 : isPhone() ? 900 : 1300);
}

function spawnParticles(count = 24) {
  if (isPhone()) {
    count = Math.min(count, 12);
  }

  const root = $("particles");
  if (!root) return;

  const fragment = document.createDocumentFragment();

  for (let i = 0; i < count; i++) {
    const particle = document.createElement("span");

    particle.className = "particle";
    particle.style.left = `${Math.random() * 100}%`;
    particle.style.top = `${30 + Math.random() * 30}%`;
    particle.style.animationDelay = `${Math.random() * 200}ms`;

    fragment.appendChild(particle);

    setTimeout(() => {
      particle.remove();
    }, 1200);
  }

  root.appendChild(fragment);
}

/* ---------- JACKPOT REVEAL ---------- */

function revealLabelClass(label) {
  return `reveal-${String(label || "").toLowerCase()}`;
}

function playRevealBonus(bonus) {
  if (!bonus || !bonus.triggered) return Promise.resolve(0);

  const overlay = $("revealOverlay");
  const cards = Array.from(document.querySelectorAll(".reveal-card"));
  const result = $("revealResult");

  if (!overlay || !cards.length || !result) {
    return Promise.resolve(0);
  }

  overlay.classList.remove("hidden");
  result.innerHTML = "";

  cards.forEach((card, index) => {
    card.disabled = false;
    card.textContent = "?";
    card.className = "reveal-card";
    card.dataset.label = bonus.symbols?.[index] || bonus.award;
  });

  let revealed = 0;

  return new Promise(resolve => {
    cards.forEach(card => {
      card.onclick = () => {
        if (card.disabled) return;

        const label = card.dataset.label;

        card.textContent = label;
        card.classList.add("revealed", revealLabelClass(label));
        card.disabled = true;

        revealed += 1;

        if (revealed === cards.length) {
          result.innerHTML = `
            <strong>${bonus.award} Jackpot!</strong>
            <span>$${money(bonus.win)}</span>
          `;

          playJackpotSound();
          spawnParticles(24);

          setTimeout(() => {
            overlay.classList.add("hidden");
            resolve(Number(bonus.win || 0));
          }, 1500);
        }
      };
    });
  });
}

/* ---------- API ---------- */

async function loadMe() {
  const res = await fetch("/api/me");
  const data = await res.json();

  updateBalance(data.balance);
  updateFreeSpins(data.freeSpins, data.freeSpinBet);
  updateJackpots(data.jackpotPools);
}

function makePreviewData() {
  const rows = getRows();
  const cols = getCols();
  const reels = [];
  const stops = [];
  const grid = [];

  for (let row = 0; row < rows; row++) {
    grid[row] = [];
  }

  for (let col = 0; col < cols; col++) {
    const reel = makeFallbackReel(120);
    const stop = 40;

    reels[col] = reel;
    stops[col] = stop;

    for (let row = 0; row < rows; row++) {
      grid[row][col] = reel[(stop + row) % reel.length];
    }
  }

  return {
    reels,
    stops,
    grid,
    winningCells: [],
    lineWins: [],
    wildMultipliers: [],
  };
}

/* ---------- BONUS BUY ---------- */

async function buyBonus() {
  if (state.spinning || state.autoFreeSpinsRunning) return;

  initAudio();

  const bet = getSelectedBet();
  const cost = bet * 100;

  if (state.balance < cost) {
    setResultBanner(`Not enough balance. Bonus buy costs <strong>$${money(cost)}</strong>.`, "bad");
    return;
  }

  const oldBalance = state.balance;
  const oldFreeSpins = state.freeSpins;
  const oldFreeSpinBet = state.freeSpinBet;

  state.spinning = true;
  state.canSkip = false;
  state.skipResolve = null;

  clearHighlights();
  clearResultBanner();
  setControlsEnabled(false);

  updateBalance(state.balance - cost);
  setResultBanner(`Buying bonus for <strong>$${money(cost)}</strong>...`, "bonus");

  let response;
  let data;

  try {
    response = await fetch("/games/fruit-fortune/api/buy-bonus", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ bet }),
    });

    data = await response.json();
  } catch (error) {
    updateBalance(oldBalance);
    updateFreeSpins(oldFreeSpins, oldFreeSpinBet);
    setResultBanner("Network error. Bonus buy failed.", "bad");
    setControlsEnabled(true);
    state.spinning = false;
    return;
  }

  if (!response.ok) {
    updateBalance(oldBalance);
    updateFreeSpins(oldFreeSpins, oldFreeSpinBet);
    setResultBanner(data.error || "Bonus buy failed.", "bad");
    setControlsEnabled(true);
    state.spinning = false;
    return;
  }

  if (!data.triggerSpin) {
    updateBalance(data.balance);
    updateFreeSpins(data.freeSpins, data.freeSpinBet);
    updateJackpots(data.jackpotPools);

    setResultBanner(
      "Bonus bought, but server did not return triggerSpin. Restart Flask and check /api/buy-bonus.",
      "bad"
    );

    setControlsEnabled(true);
    state.spinning = false;
    return;
  }

  const triggerSpin = {
    ...data.triggerSpin,
    balance: data.balance,
    freeSpins: data.freeSpins,
    freeSpinBet: data.freeSpinBet,
    jackpotPools: data.jackpotPools,
  };

  playSpinStartSound();

  const renderedTrigger = renderSpinStrips(triggerSpin);
  state.lastData = renderedTrigger;

  await animateToStops(renderedTrigger);

  highlightWinningSymbols(renderedTrigger);
  drawWinLines(renderedTrigger);
  renderWinList(renderedTrigger);

  playJackpotSound();
  spawnParticles(30);

  setResultBanner(
    `3 scatters landed! <strong>${data.bonusSpinsAwarded || 10} free spins</strong> triggered.`,
    "bonus"
  );

  await sleep(1100);

  updateBalance(data.balance);
  updateFreeSpins(data.freeSpins, data.freeSpinBet);
  updateJackpots(data.jackpotPools);

  state.spinning = false;
  setControlsEnabled(true);
  updateSpinButtonText();

  setResultBanner(
    `Bonus active. Playing <strong>${data.bonusSpinsAwarded || 10} free spins</strong> with wild multipliers.`,
    "bonus"
  );

  await sleep(900);
  autoPlayFreeSpins();
}

/* ---------- SPIN ---------- */

async function spin() {
  if (state.spinning) {
    requestSkip();
    return;
  }

  initAudio();
  playSpinStartSound();

  syncResponsiveSlotSize();

  const bet = getSelectedBet();
  const usingFreeSpin = state.freeSpins > 0;
  const chargedBet = usingFreeSpin ? 0 : bet;

  if (!usingFreeSpin && state.balance < bet) {
    setResultBanner("Not enough balance for this bet.", "bad");
    return;
  }

  state.spinning = true;
  state.canSkip = false;
  state.skipResolve = null;

  clearHighlights();
  clearResultBanner();
  setControlsEnabled(false);

  const oldBalance = state.balance;
  const oldFreeSpins = state.freeSpins;
  const oldFreeSpinBet = state.freeSpinBet;

  if (usingFreeSpin) {
    updateFreeSpins(state.freeSpins - 1, state.freeSpinBet);
  } else {
    updateBalance(state.balance - chargedBet);
  }

  let response;
  let rawData;

  try {
    response = await fetch("/games/fruit-fortune/api/spin", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ bet }),
    });

    rawData = await response.json();
  } catch (error) {
    updateBalance(oldBalance);
    updateFreeSpins(oldFreeSpins, oldFreeSpinBet);
    setResultBanner("Network error. Try again.", "bad");
    setControlsEnabled(true);
    state.spinning = false;
    return;
  }

  if (!response.ok) {
    updateBalance(oldBalance);
    updateFreeSpins(oldFreeSpins, oldFreeSpinBet);
    setResultBanner(rawData.error || "Something went wrong.", "bad");
    setControlsEnabled(true);
    state.spinning = false;
    return;
  }

  const data = renderSpinStrips(rawData);
  state.lastData = data;

  await animateToStops(data);

  highlightWinningSymbols(data);
  drawWinLines(data);
  renderWinList(data);

  const pendingJackpot = data.revealBonus && data.revealBonus.triggered
    ? Number(data.revealBonus.win || 0)
    : 0;

  updateBalance(Number(data.balance || 0) - pendingJackpot);
  updateFreeSpins(data.freeSpins, data.freeSpinBet);
  updateJackpots(data.jackpotPools);

  const totalWin = Number(data.win || data.totalWin || 0) + Number(data.jackpotWin || data.jackpot_win || 0);

  if (totalWin > 0) {
    playWinSound(totalWin);
    setResultBanner(`Win <strong>$${money(totalWin)}</strong>`, "win");
    showWinOverlay(totalWin);
    spawnParticles(totalWin >= 100 ? 28 : 14);
  } else if (String(data.mode || "") === "free") {
    playNoWinSound();
    setResultBanner(`Free spin complete. <strong>${data.freeSpins || 0}</strong> remaining.`, "bonus");
  } else {
    playNoWinSound();
    setResultBanner("No win. Try again.", "");
  }

  if (data.revealBonus && data.revealBonus.triggered) {
    playJackpotSound();
    setResultBanner("Jackpot Reveal Triggered!", "bonus");

    await playRevealBonus(data.revealBonus);

    updateBalance(data.balance);
    updateJackpots(data.jackpotPools);

    setResultBanner(
      `${data.revealBonus.award} Jackpot Won: <strong>$${money(data.revealBonus.win)}</strong>`,
      "bonus"
    );
  }

  setControlsEnabled(true);
  state.spinning = false;
  updateSpinButtonText();

  if (state.autoFreeSpinsRunning && state.freeSpins <= 0) {
    setResultBanner("Bonus complete.", "bonus");
  }
}

async function autoPlayFreeSpins() {
  if (state.autoFreeSpinsRunning) return;

  state.autoFreeSpinsRunning = true;
  setControlsEnabled(false);

  while (state.freeSpins > 0) {
    await sleep(850);

    if (!state.autoFreeSpinsRunning) break;

    await spin();
  }

  state.autoFreeSpinsRunning = false;
  setControlsEnabled(true);
  updateSpinButtonText();
}

/* ---------- LOAD CONFIG ---------- */

async function loadConfig() {
  const res = await fetch("/games/fruit-fortune/api/config");
  cfg = await res.json();

  syncResponsiveSlotSize();

  const preview = makePreviewData();
  state.previewData = preview;

  renderSpinStrips(preview);
  setReelsToStops(preview);

  if (cfg.user) {
    updateBalance(cfg.user.balance);
    updateFreeSpins(cfg.user.freeSpins, cfg.user.freeSpinBet);
  }

  if (cfg.jackpotPools) {
    updateJackpots(cfg.jackpotPools);
  }
}

/* ---------- RESIZE ---------- */

function rerenderCurrentBoard() {
  if (!cfg || state.spinning) return;

  syncResponsiveSlotSize();

  const data = state.lastData || state.previewData;
  if (!data) return;

  const rendered = renderSpinStrips(data);
  setReelsToStops(rendered);
  highlightWinningSymbols(rendered);
  drawWinLines(rendered);
}

/* ---------- INIT ---------- */

function bindControls() {
  const spinBtn = $("spinBtn");
  const turboBtn = $("turboBtn");
  const maxBtn = $("maxBtn");
  const betInput = $("bet");
  const buyBonusBtn = $("buyBonusBtn");

  if (spinBtn) {
    spinBtn.addEventListener("click", spin);
  }

  if (buyBonusBtn) {
    buyBonusBtn.addEventListener("click", buyBonus);
  }

  if (turboBtn) {
    turboBtn.addEventListener("click", () => {
      state.turbo = !state.turbo;
      turboBtn.classList.toggle("active", state.turbo);
    });
  }

  if (maxBtn && betInput) {
    maxBtn.addEventListener("click", () => {
      betInput.value = Math.max(1, Math.floor(state.balance));
      updateBuyBonusCost();
    });
  }

  if (betInput) {
    betInput.addEventListener("input", updateBuyBonusCost);
    betInput.addEventListener("change", updateBuyBonusCost);
  }

  document.addEventListener("keydown", event => {
    if (event.code !== "Space") return;

    const tag = document.activeElement?.tagName?.toLowerCase();
    if (tag === "input" || tag === "select" || tag === "textarea") return;

    event.preventDefault();

    if (state.spinning) {
      requestSkip();
    } else {
      spin();
    }
  });

  window.addEventListener("resize", () => {
    if (!cfg || state.spinning) return;

    clearTimeout(state.resizeTimer);

    state.resizeTimer = setTimeout(() => {
      rerenderCurrentBoard();
    }, 150);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  bindControls();

  try {
    await loadConfig();
    await loadMe();
    updateBuyBonusCost();
    updateSpinButtonText();
  } catch (error) {
    setResultBanner("Could not load slot. Refresh the page.", "bad");
  }
});

