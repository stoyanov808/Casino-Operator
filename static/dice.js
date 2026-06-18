function $(id) {
  return document.getElementById(id);
}

function money(value) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

const diceState = {
  rolling: false,
  balance: 1000,
  currentFace: 1,
  rotX: 0,
  rotY: 0,
  rotZ: 0,
};

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function nextFrame() {
  return new Promise(resolve => requestAnimationFrame(resolve));
}

function updateJackpots(pools) {
  if (!pools) return;

  $("jackpotGrand").textContent = money(pools.GRAND ?? 10000);
  $("jackpotMajor").textContent = money(pools.MAJOR ?? 1500);
  $("jackpotMinor").textContent = money(pools.MINOR ?? 250);
  $("jackpotMini").textContent = money(pools.MINI ?? 50);
}

function updateBalance(value) {
  diceState.balance = Number(value || 0);

  const balanceEl = $("balance");
  if (balanceEl) {
    balanceEl.textContent = money(diceState.balance);
  }
}

function setBanner(message, type = "") {
  const banner = $("resultBanner");
  if (!banner) return;

  banner.className = `result-banner ${type}`;
  banner.innerHTML = message;
  banner.classList.remove("hidden");
}

function randomTurns(min = 2, max = 5) {
  return 360 * (min + Math.floor(Math.random() * (max - min + 1)));
}

function faceRotation(value) {
  switch (Number(value)) {
    case 1:
      return { x: 0, y: 0, z: 0 };
    case 2:
      return { x: -90, y: 0, z: 0 };
    case 3:
      return { x: 0, y: -90, z: 0 };
    case 4:
      return { x: 0, y: 90, z: 0 };
    case 5:
      return { x: 90, y: 0, z: 0 };
    case 6:
      return { x: 0, y: 180, z: 0 };
    default:
      return { x: 0, y: 0, z: 0 };
  }
}

function setCubeTransform(x, y, z, transition = false) {
  const cube = $("diceCube");
  if (!cube) return;

  cube.style.transition = transition
    ? "transform 700ms cubic-bezier(.16,.9,.22,1)"
    : "none";

  cube.style.transform = `rotateX(${x}deg) rotateY(${y}deg) rotateZ(${z}deg)`;
}

function setDiceFace(value, transition = false) {
  const rot = faceRotation(value);

  diceState.currentFace = Number(value);
  diceState.rotX = rot.x;
  diceState.rotY = rot.y;
  diceState.rotZ = rot.z;

  setCubeTransform(rot.x, rot.y, rot.z, transition);
}

function startPreRoll() {
  const cube = $("diceCube");
  const scene = $("diceScene");
  const shadow = $("diceShadow");

  diceState.rolling = true;

  if (cube) {
    cube.classList.remove("dice-settle-pop");
    cube.classList.add("dice-pre-roll");
  }

  if (scene) {
    scene.classList.add("dice-table-bob");
  }

  if (shadow) {
    shadow.classList.add("rolling");
  }
}

function stopPreRoll() {
  const cube = $("diceCube");
  const scene = $("diceScene");
  const shadow = $("diceShadow");

  if (cube) {
    cube.classList.remove("dice-pre-roll");
  }

  if (scene) {
    scene.classList.remove("dice-table-bob");
  }

  if (shadow) {
    shadow.classList.remove("rolling");
  }
}

async function playTrue3dRoll(finalFace) {
  const cube = $("diceCube");
  const scene = $("diceScene");

  if (!cube || !scene) return;

  stopPreRoll();

  const finalRot = faceRotation(finalFace);

  const startX = diceState.rotX + randomTurns(3, 5) + 135;
  const startY = diceState.rotY + randomTurns(3, 5) + 240;
  const startZ = diceState.rotZ + randomTurns(1, 3) + 45;

  const targetX = finalRot.x + randomTurns(2, 4);
  const targetY = finalRot.y + randomTurns(2, 4);
  const targetZ = finalRot.z + randomTurns(1, 2);

  cube.getAnimations().forEach(animation => animation.cancel());
  scene.getAnimations().forEach(animation => animation.cancel());

  cube.style.transition = "none";
  scene.style.transition = "none";

  cube.style.transform = `rotateX(${startX}deg) rotateY(${startY}deg) rotateZ(${startZ}deg)`;
  scene.style.transform = "translate3d(-105px, -14px, 0) rotateZ(-12deg)";

  await nextFrame();
  await nextFrame();

  const cubeAnimation = cube.animate(
    [
      {
        transform: `rotateX(${startX}deg) rotateY(${startY}deg) rotateZ(${startZ}deg) scale3d(1, 1, 1)`,
        offset: 0,
        easing: "linear",
      },
      {
        transform: `rotateX(${startX + 360}deg) rotateY(${startY + 480}deg) rotateZ(${startZ + 160}deg) scale3d(1.04, .96, 1.04)`,
        offset: 0.28,
        easing: "linear",
      },
      {
        transform: `rotateX(${startX + 760}deg) rotateY(${startY + 850}deg) rotateZ(${startZ + 300}deg) scale3d(.98, 1.04, .98)`,
        offset: 0.58,
        easing: "linear",
      },
      {
        transform: `rotateX(${targetX + 24}deg) rotateY(${targetY - 18}deg) rotateZ(${targetZ + 11}deg) scale3d(1.05, .95, 1.05)`,
        offset: 0.88,
        easing: "cubic-bezier(.08,.82,.13,1)",
      },
      {
        transform: `rotateX(${targetX}deg) rotateY(${targetY}deg) rotateZ(${targetZ}deg) scale3d(1, 1, 1)`,
        offset: 1,
        easing: "cubic-bezier(.16,.95,.25,1)",
      },
    ],
    {
      duration: 3400,
      fill: "forwards",
    }
  );

  const sceneAnimation = scene.animate(
    [
      {
        transform: "translate3d(-105px, -14px, 0) rotateZ(-12deg)",
        offset: 0,
        easing: "ease-out",
      },
      {
        transform: "translate3d(-35px, -72px, 0) rotateZ(10deg)",
        offset: 0.32,
        easing: "ease-out",
      },
      {
        transform: "translate3d(80px, -18px, 0) rotateZ(-7deg)",
        offset: 0.72,
        easing: "ease-in",
      },
      {
        transform: "translate3d(20px, 10px, 0) rotateZ(3deg)",
        offset: 0.9,
        easing: "ease-out",
      },
      {
        transform: "translate3d(0, 0, 0) rotateZ(0deg)",
        offset: 1,
        easing: "ease-out",
      },
    ],
    {
      duration: 3000,
      fill: "forwards",
    }
  );

  await Promise.all([
    cubeAnimation.finished.catch(() => {}),
    sceneAnimation.finished.catch(() => {}),
  ]);

  cube.style.transition = "none";
  scene.style.transition = "none";

  cube.style.transform = `rotateX(${finalRot.x}deg) rotateY(${finalRot.y}deg) rotateZ(${finalRot.z}deg)`;
  scene.style.transform = "translate3d(0, 0, 0) rotateZ(0deg)";

  diceState.currentFace = Number(finalFace);
  diceState.rotX = finalRot.x;
  diceState.rotY = finalRot.y;
  diceState.rotZ = finalRot.z;

  cube.classList.remove("dice-settle-pop");
  void cube.offsetWidth;
  cube.classList.add("dice-settle-pop");

  await sleep(700);
}

function revealLabelClass(label) {
  return `reveal-${String(label || "").toLowerCase()}`;
}

function playRevealBonus(bonus) {
  if (!bonus || !bonus.triggered) return Promise.resolve(0);

  const overlay = $("revealOverlay");
  const cards = Array.from(document.querySelectorAll(".reveal-card"));
  const result = $("revealResult");

  overlay.classList.remove("hidden");
  result.innerHTML = "";

  cards.forEach((card, idx) => {
    card.disabled = false;
    card.textContent = "?";
    card.className = "reveal-card";
    card.dataset.label = bonus.symbols[idx] || bonus.award;
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

        if (revealed === 3) {
          result.innerHTML = `
            <strong>${bonus.award} Jackpot!</strong>
            <span>$${money(bonus.win)}</span>
          `;

          setTimeout(() => {
            overlay.classList.add("hidden");
            resolve(bonus.win || 0);
          }, 1500);
        }
      };
    });
  });
}

async function loadMe() {
  const data = await fetch("/api/me").then(res => res.json());

  updateBalance(data.balance);
  updateJackpots(data.jackpotPools);
}

async function rollDice() {
  if (diceState.rolling) return;

  const bet = Math.max(1, parseInt($("bet").value || "1", 10));
  const pick = parseInt($("pick").value, 10);
  const rollBtn = $("rollBtn");

  if (diceState.balance < bet) {
    setBanner("Not enough balance for this bet.", "bad");
    return;
  }

  diceState.rolling = true;

  rollBtn.disabled = true;
  rollBtn.textContent = "Rolling...";

  updateBalance(diceState.balance - bet);
  setBanner("Rolling the dice...", "");

  startPreRoll();

  const requestStarted = performance.now();

  let response;
  let data;

  try {
    response = await fetch("/games/dice/api/play", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ bet, pick }),
    });

    data = await response.json();
  } catch (error) {
    stopPreRoll();
    updateBalance(diceState.balance + bet);
    setBanner("Network error. Try again.", "bad");

    diceState.rolling = false;
    rollBtn.disabled = false;
    rollBtn.textContent = "Roll Dice";
    return;
  }

  const elapsed = performance.now() - requestStarted;
  const minimumPreRoll = 650;

  if (elapsed < minimumPreRoll) {
    await sleep(minimumPreRoll - elapsed);
  }

  if (!response.ok) {
    stopPreRoll();
    updateBalance(diceState.balance + bet);
    setBanner(data.error || "Something went wrong.", "bad");

    diceState.rolling = false;
    rollBtn.disabled = false;
    rollBtn.textContent = "Roll Dice";
    return;
  }

  await playTrue3dRoll(data.roll);

  const pendingJackpot = data.revealBonus && data.revealBonus.triggered
    ? Number(data.revealBonus.win || 0)
    : 0;

  updateBalance(Number(data.balance || 0) - pendingJackpot);
  updateJackpots(data.jackpotPools);

  if (data.win > 0) {
    setBanner(`You hit ${data.roll}. Win <strong>$${money(data.win)}</strong>`, "win");
  } else {
    setBanner(`Rolled ${data.roll}. No win.`, "");
  }

  if (data.revealBonus && data.revealBonus.triggered) {
    setBanner("Jackpot Reveal Triggered!", "bonus");

    await playRevealBonus(data.revealBonus);

    updateBalance(data.balance);
    updateJackpots(data.jackpotPools);

    setBanner(`${data.revealBonus.award} Jackpot Won: <strong>$${money(data.revealBonus.win)}</strong>`, "bonus");
  }

  diceState.rolling = false;
  rollBtn.disabled = false;
  rollBtn.textContent = "Roll Dice";
}

document.addEventListener("DOMContentLoaded", () => {
  setDiceFace(1, false);

  const rollBtn = $("rollBtn");

  if (rollBtn) {
    rollBtn.addEventListener("click", rollDice);
  }

  loadMe();
});