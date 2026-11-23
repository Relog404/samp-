/* RELOG-IC client panel — фронтенд без зависимостей */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const SPLASHES = [
  "Оптимизация!", "60 FPS — это мало!", "Тоже оптимизация!",
  "Настрой и играй!", "MAX FPS!", "Бодикам?", "Рыбий глаз included",
];

const GROUPS = {
  graphics: {
    title: "Графика",
    keys: ["renderDistance", "mipmapLevels", "fancyGraphics", "ao", "renderClouds",
           "gamma", "fullscreen", "guiScale", "anaglyph3d"],
  },
  camera: {
    title: "Камера",
    keys: ["fov", "smoothCamera", "bobView", "mouseSensitivity", "invertYMouse"],
  },
  perf: {
    title: "Производительность",
    keys: ["maxFps", "particles", "useVbo", "fboEnable", "enableVsync"],
  },
  misc: {
    title: "Прочее",
    keys: ["chatVisibility", "chatOpacity", "chatScale", "attackIndicator", "mainHand",
           "heldItemTooltips", "pauseOnLostFocus", "hideServerAddress", "snooperEnabled",
           "touchscreen", "advancedItemTooltips", "reducedDebugInfo"],
  },
};

const LABELS = {
  renderDistance: ["Дальность прорисовки", "Сколько чанков грузится вокруг: меньше — больше FPS."],
  mipmapLevels: ["Mipmap / сглаживание текстур", "0 — резко и быстро, 4 — мягкие текстуры вдали."],
  fancyGraphics: ["Красивая графика", "Листва, вода и тени в полном качестве."],
  ao: ["Ambient Occlusion", "Мягкие тени по углам блоков."],
  renderClouds: ["Облака", "Облака в мире: выключить — минус нагрузка."],
  gamma: ["Яркость", "Гамма: 0 — темно, 1 — «фоторежим» без мода на свет."],
  fullscreen: ["Полный экран", "Эксклюзивный фуллскрин."],
  guiScale: ["Масштаб интерфейса", "0 — авто, 1..3 — фиксированный."],
  anaglyph3d: ["Anaglyph 3D", "Красно-синие очки. Почти никогда не нужно."],
  fov: ["Угол обзора (FOV)", "70°..110°. 110° — «рыбий глаз», 85° — бодикам."],
  smoothCamera: ["Плавная камера", "Камера догоняет движение — эффект бодикама."],
  bobView: ["Покачивание камеры", "Ходьба/бег качают камеру."],
  mouseSensitivity: ["Чувствительность мыши", "Ниже — плавнее и кинематографичнее."],
  invertYMouse: ["Инверсия Y", "Для тех, кто привык к обратной вертикали."],
  maxFps: ["Лимит FPS", "Ограничение кадров: 260 — «без лимита» для 1.12.2."],
  particles: ["Частицы", "Все / уменьшено / минимум — самый быстрый профиль."],
  useVbo: ["VBO", "Быстрая отрисовка чанков. Держать включённым."],
  fboEnable: ["FBO", "Фреймбуферы: нужны для пост-эффектов."],
  enableVsync: ["V-Sync", "Синхронизация с монитором: меньше разрывов, больше инпута."],
  chatOpacity: ["Прозрачность чата", "Насколько чат перекрывает мир."],
  chatScale: ["Масштаб чата", "Размер текста чата."],
  pauseOnLostFocus: ["Пауза при потере фокуса", "Сворачивание игры ставит паузу."],
  touchscreen: ["Сенсорный режим", "Для планшетов."],
  advancedItemTooltips: ["Продвинутые подсказки", "ID и прочее в тултипах предметов."],
  reducedDebugInfo: ["Урезанный F3", "Меньше строк в отладочном экране."],
  chatVisibility: ["Видимость чата", "Полный / только команды / скрыт."],
  attackIndicator: ["Индикатор атаки", "Выкл / крестик / полоса перезарядки."],
  mainHand: ["Основная рука", "Правая или левая."],
  snooperEnabled: ["Snooper (телеметрия)", "Выключи — клиент не собирает статистику."],
  hideServerAddress: ["Скрывать адрес сервера", "Не показывать IP в меню."],
  heldItemTooltips: ["Тултипы предметов", "Показывать название предмета в руке."],
};

const state = {
  status: null,
  options: {},
  snapshot: {},
  spec: {},
  group: "graphics",
  presets: [],
  profiles: [],
};

/* ------------------------------ утилиты ------------------------------ */

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function toast(text, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.innerHTML = text;
  $("#toasts").append(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transform = "translateY(6px)"; }, 4200);
  setTimeout(() => el.remove(), 4800);
}

function fmt(key, value) {
  if (typeof value === "boolean") return value ? "вкл" : "выкл";
  if (key === "fov") return `${Math.round(70 + 40 * Number(value))}°`;
  if (key === "particles") return ["все", "уменьшено", "минимум"][Number(value)] || value;
  if (key === "guiScale") return Number(value) === 0 ? "авто" : String(value);
  if (key === "gamma") return `${Math.round(Number(value) * 100)}%`;
  if (key === "maxFps") return Number(value) >= 260 ? "∞" : `${value}`;
  if (key === "chatVisibility") return ["полный", "только команды", "скрыт"][Number(value)] || value;
  if (key === "attackIndicator") return ["выкл", "крестик", "полоса"][Number(value)] || value;
  if (key === "mainHand") return value === "left" ? "левая" : "правая";
  if (key === "mouseSensitivity" || key === "chatOpacity" || key === "chatScale") {
    return `${Math.round(Number(value) * 100)}%`;
  }
  return String(value);
}

function showScreen(name) {
  $$(".screen").forEach((s) => s.classList.toggle("active", s.id === `screen-${name}`));
  $$(".mc-btn[data-screen]").forEach((b) => b.classList.toggle("active", b.dataset.screen === name));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ------------------------------ рендер ------------------------------ */

function renderStatus() {
  const s = state.status || {};
  $("#stat-options").textContent = s.options ? "есть" : "нет";
  $("#stat-profiles").textContent = s.profiles ? "есть" : "нет";
  $("#stat-jars").textContent = (s.jars || []).length ? `${s.jars.length} шт.` : "нет";
  $("#stat-dir").textContent = s.minecraftDir || "—";
  $("#pill-dir").textContent = s.minecraftDir || ".minecraft";
  $("#about-version").textContent = s.version || "—";
  $("#about-dir").textContent = s.dir || s.minecraftDir || "—";
  $("#dir-input").value = s.minecraftDir || "";

  const list = $("#jar-list");
  list.innerHTML = "";
  (s.jars || []).forEach((jar) => {
    const opt = document.createElement("option");
    opt.value = jar;
    list.append(opt);
  });
  if (!$("#jar-source").value && (s.jars || []).length) $("#jar-source").value = s.jars[0];
}

function renderControls() {
  const box = $("#controls");
  box.innerHTML = "";
  const group = GROUPS[state.group];
  if (!group) return;

  group.keys.forEach((key) => {
    const spec = state.spec[key] || {};
    const value = state.options[key];
    if (value === undefined) return;
    const [name, desc] = LABELS[key] || [key, ""];

    const row = document.createElement("div");
    row.className = "ctl";

    const left = document.createElement("div");
    left.innerHTML = `<div class="ctl-name">${name}</div><div class="ctl-desc">${desc}</div>`;

    const side = document.createElement("div");
    side.className = "ctl-side";

    if (spec.type === "bool") {
      const label = document.createElement("label");
      label.className = "switch";
      label.innerHTML = `<input type="checkbox" ${value ? "checked" : ""} />
                         <span class="knob"></span>`;
      label.querySelector("input").addEventListener("change", (e) => {
        state.options[key] = e.target.checked;
        updateChanges();
      });
      side.append(label);
      const txt = document.createElement("span");
      txt.className = "ctl-val";
      txt.textContent = fmt(key, value);
      side.append(txt);
    } else if (spec.type === "enum" || spec.type === "str_enum") {
      const sel = document.createElement("select");
      spec.choices.forEach((choice) => {
        const opt = document.createElement("option");
        opt.value = choice;
        opt.textContent = fmt(key, choice);
        if (String(choice) === String(value)) opt.selected = true;
        sel.append(opt);
      });
      sel.addEventListener("change", (e) => {
        state.options[key] = spec.type === "str_enum" ? e.target.value : Number(e.target.value);
        updateChanges();
      });
      side.append(sel);
    } else {
      const val = document.createElement("span");
      val.className = "ctl-val";
      val.id = `val-${key}`;
      val.textContent = fmt(key, value);

      const range = document.createElement("input");
      range.type = "range";
      range.min = spec.min;
      range.max = spec.max;
      range.step = spec.step || 1;
      range.value = value;
      range.addEventListener("input", (e) => {
        const v = Number(e.target.value);
        state.options[key] = v;
        val.textContent = fmt(key, v);
        updateChanges();
      });
      side.append(range, val);
    }

    row.append(left, side);
    box.append(row);
  });
}

function updateChanges() {
  const changed = Object.keys(state.options).filter(
    (k) => state.options[k] !== state.snapshot[k],
  );
  $("#opt-changes").textContent = `изменений: ${changed.length}`;
  $("#btn-apply").disabled = changed.length === 0;
}

async function loadOptions() {
  const data = await api("/api/options");
  state.options = { ...data.values };
  state.snapshot = { ...data.values };
  state.spec = data.spec || {};
  renderControls();
  updateChanges();
  $("#opt-status").textContent = data.exists
    ? `options.txt: ${data.path}`
    : "options.txt не найден — будет создан при применении";
}

async function loadPresets() {
  const data = await api("/api/presets");
  state.presets = data.presets || [];
  const grid = $("#preset-grid");
  grid.innerHTML = "";
  state.presets.forEach((preset) => {
    const card = document.createElement("button");
    card.className = "preset";
    card.dataset.tag = preset.tag;
    card.innerHTML = `
      <h3>${preset.name}</h3>
      <p>${preset.about}</p>
      <div class="tags">
        ${Object.keys(preset.values).slice(0, 4).map((k) => `<span class="tag">${k}</span>`).join("")}
      </div>`;
    card.addEventListener("click", () => applyPreset(preset.id));
    grid.append(card);
  });
}

async function applyPreset(id) {
  try {
    const res = await api("/api/preset", { method: "POST", body: { id } });
    toast(`<b>${res.preset.name}</b> — изменено ${res.count} параметров`, "ok");
    $("#preset-status").textContent = `применено: ${res.preset.name} · бэкап: ${res.backup || "—"}`;
    await Promise.all([loadOptions(), refreshStatus()]);
  } catch (err) {
    toast(`Ошибка: ${err.message}`, "err");
  }
}

async function applyOptions() {
  const values = {};
  Object.keys(state.options).forEach((key) => {
    if (state.options[key] !== state.snapshot[key]) values[key] = state.options[key];
  });
  if (!Object.keys(values).length) return;
  try {
    const res = await api("/api/options", { method: "POST", body: { values } });
    toast(`Записано параметров: <b>${res.count}</b>`, "ok");
    $("#opt-status").textContent = `бэкап: ${res.backup || "—"}`;
    await loadOptions();
  } catch (err) {
    toast(`Ошибка: ${err.message}`, "err");
  }
}

async function refreshStatus() {
  state.status = await api("/api/status");
  renderStatus();
}

/* ------------------------------ JVM ------------------------------ */

function jvmPreview() {
  const mem = Number($("#jvm-mem").value);
  const gc = $("#jvm-gc").value;
  const extra = $("#jvm-extra").value.trim();
  const flags = {
    aikar: "-XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+DisableExplicitGC …",
    g1: "-XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=50",
    none: "(только память)",
  }[gc];
  $("#jvm-mem-label").textContent = `${mem} МБ`;
  $("#jvm-preview").textContent =
    `-Xms${Math.floor(mem / 2)}M -Xmx${mem}M ${gc === "none" ? "" : flags} ${extra}`.trim();
}

async function loadProfiles() {
  try {
    const data = await api("/api/profiles");
    state.profiles = data.profiles || [];
    const sel = $("#jvm-profile");
    sel.innerHTML = "";
    if (!state.profiles.length) {
      const opt = document.createElement("option");
      opt.textContent = "профили не найдены";
      opt.value = "";
      sel.append(opt);
      $("#jvm-status").textContent = data.warning || "нет launcher_profiles.json";
      return;
    }
    state.profiles.forEach((profile) => {
      const opt = document.createElement("option");
      opt.value = profile.key;
      opt.textContent = `${profile.name}${profile.selected ? " · выбран" : ""}`;
      if (profile.javaArgs) opt.dataset.args = profile.javaArgs;
      sel.append(opt);
    });
    $("#jvm-status").textContent =
      `профиль по умолчанию: ${(state.profiles.find((p) => p.selected) || state.profiles[0]).name}`;
  } catch (err) {
    $("#jvm-status").textContent = `ошибка: ${err.message}`;
  }
}

async function applyJvm() {
  const profile = $("#jvm-profile").value;
  if (!profile) { toast("Профиль не выбран", "err"); return; }
  const body = {
    profile,
    gc: $("#jvm-gc").value,
    maxMemoryMB: Number($("#jvm-mem").value),
    extra: $("#jvm-extra").value,
  };
  try {
    const res = await api("/api/jvm", { method: "POST", body });
    toast(`JVM-аргументы записаны в <b>${res.profile}</b>`, "ok");
    $("#jvm-status").textContent = `бэкап: ${res.backup}`;
    $("#jvm-preview").textContent = res.new;
  } catch (err) {
    toast(`Ошибка: ${err.message}`, "err");
  }
}

/* ------------------------------ jar ------------------------------ */

async function patchJar() {
  const source = $("#jar-source").value.trim();
  if (!source) { toast("Укажи исходный jar", "err"); return; }
  const log = $("#jar-log");
  log.textContent = "пересобираю…";
  try {
    const res = await api("/api/jar/patch", {
      method: "POST",
      body: { source, name: $("#jar-name").value.trim() || "1.12.2-relogic.jar",
              stripAllScreens: $("#jar-full").checked },
    });
    log.textContent =
      `готово: ${res.output}\nразмер: ${(res.size / 1048576).toFixed(1)} MiB` +
      `\nкастомные экраны клиента: ${res.stripAllScreens ? "выключены" : "включены"}`;
    toast("Jar пересобран", "ok");
    await refreshStatus();
  } catch (err) {
    log.textContent = `ошибка: ${err.message}`;
    toast(`Ошибка: ${err.message}`, "err");
  }
}

async function verifyJar() {
  const source = $("#jar-source").value.trim();
  if (!source) { toast("Укажи исходный jar", "err"); return; }
  const output = `dist/${$("#jar-name").value.trim() || "1.12.2-relogic.jar"}`;
  $("#jar-log").textContent = "проверяю…";
  try {
    const res = await api("/api/jar/verify", { method: "POST", body: { source, output } });
    $("#jar-log").textContent = (res.stdout || "") + (res.stderr ? `\n${res.stderr}` : "");
    toast(res.code === 0 ? "Проверка пройдена" : "Проверка не пройдена",
          res.code === 0 ? "ok" : "err");
  } catch (err) {
    $("#jar-log").textContent = `ошибка: ${err.message}`;
  }
}

async function setDir() {
  const path = $("#dir-input").value.trim();
  if (!path) { toast("Укажи путь", "err"); return; }
  try {
    const res = await api("/api/dir", { method: "POST", body: { path } });
    toast(`Папка: <b>${res.minecraftDir}</b>${res.warning ? " (не найдена)" : ""}`,
          res.warning ? "err" : "ok");
    await refreshStatus();
    await Promise.all([loadOptions(), loadProfiles()]);
  } catch (err) {
    toast(`Ошибка: ${err.message}`, "err");
  }
}

async function useDemo() {
  try {
    const res = await api("/api/demo", { method: "POST", body: {} });
    toast("Включена демо-папка", "ok");
    $("#dir-input").value = res.minecraftDir;
    await refreshStatus();
    await Promise.all([loadOptions(), loadProfiles()]);
  } catch (err) {
    toast(`Ошибка: ${err.message}`, "err");
  }
}

/* ------------------------------ init ------------------------------ */

function bindEvents() {
  $$("[data-screen]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.screen;
      showScreen(target);
      if (target === "optimization") loadOptions().catch((e) => toast(e.message, "err"));
      if (target === "jvm") loadProfiles();
    });
  });

  $$("#opt-tabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$("#opt-tabs .tab").forEach((t) => t.classList.toggle("active", t === tab));
      state.group = tab.dataset.group;
      renderControls();
    });
  });

  $("#btn-apply").addEventListener("click", applyOptions);
  $("#btn-reload").addEventListener("click", () => loadOptions().catch((e) => toast(e.message, "err")));
  $("#btn-refresh").addEventListener("click", () => refreshAll());
  $("#btn-dir").addEventListener("click", setDir);
  $("#btn-demo").addEventListener("click", useDemo);
  $("#btn-jar-patch").addEventListener("click", patchJar);
  $("#btn-jar-verify").addEventListener("click", verifyJar);
  $("#btn-jars").addEventListener("click", () => refreshStatus());
  $("#btn-jvm").addEventListener("click", applyJvm);

  ["#jvm-mem", "#jvm-gc", "#jvm-extra"].forEach((sel) =>
    $(sel).addEventListener("input", jvmPreview));

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") showScreen("main");
  });
}

async function refreshAll() {
  try {
    await refreshStatus();
    await Promise.all([loadOptions(), loadPresets(), loadProfiles()]);
    $("#foot-status").textContent = "готов";
  } catch (err) {
    toast(`Не удалось загрузить состояние: ${err.message}`, "err");
    $("#foot-status").textContent = "ошибка";
  }
}

async function init() {
  $("#splash").textContent = SPLASHES[Math.floor(Math.random() * SPLASHES.length)];
  setInterval(() => {
    $("#splash").textContent = SPLASHES[Math.floor(Math.random() * SPLASHES.length)];
  }, 5200);

  bindEvents();
  jvmPreview();
  await refreshAll();
}

init();
