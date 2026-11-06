const $ = (id) => document.getElementById(id);

const params = new URLSearchParams(location.search);
const token = params.get("token") || sessionStorage.getItem("lorekeeper-studio-token") || "";
if (params.get("token")) {
  sessionStorage.setItem("lorekeeper-studio-token", params.get("token"));
}

const state = {
  courses: [],
  modules: [],
  current: null,
  templates: {},
  kinds: [],
  lessons: [],
  selectedLesson: null,
  dirty: false,
};

async function api(path, options = {}) {
  const headers = { "X-Studio-Token": token, ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { error: text };
    }
  }
  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  return data;
}

function setStatus(message, kind = "") {
  const el = $("status");
  el.textContent = message;
  el.className = `status ${kind}`.trim();
}

function renderProblems(problems = []) {
  const list = $("problems-list");
  list.textContent = "";
  const count = $("problem-count");
  count.textContent = problems.length ? `${problems.length} issue${problems.length === 1 ? "" : "s"}` : "";
  if (!problems.length) {
    const item = document.createElement("li");
    item.className = "ok";
    item.textContent = "No problems found.";
    list.append(item);
    return;
  }
  for (const problem of problems) {
    const item = document.createElement("li");
    item.textContent = problem;
    list.append(item);
  }
}

function renderLessons(lessons = []) {
  const list = $("lesson-list");
  list.textContent = "";
  const count = $("lesson-count");
  count.textContent = lessons.length ? `${lessons.length}` : "";
  if (!lessons.length) {
    const item = document.createElement("li");
    item.className = "empty";
    item.textContent = "No lessons in this overlay yet.";
    list.append(item);
    return;
  }
  for (const lesson of lessons) {
    const item = document.createElement("li");
    if (lesson.id === state.selectedLesson) item.classList.add("selected");
    const title = document.createElement("div");
    title.textContent = `${lesson.id} · ${lesson.title}`;
    const meta = document.createElement("div");
    meta.className = "lesson-meta";
    meta.textContent = `${lesson.kind} · ${lesson.xp} XP`;
    item.append(title, meta);
    item.addEventListener("click", () => {
      state.selectedLesson = lesson.id;
      renderLessons(state.lessons);
    });
    list.append(item);
  }
}

function currentModuleNumber() {
  const module = state.modules.find((item) => item.slug === $("module").value);
  return module ? module.number : 1;
}

function nextLessonId() {
  const moduleNumber = String(currentModuleNumber()).padStart(2, "0");
  let highest = 0;
  for (const lesson of state.lessons) {
    const match = /^(\d{2})-(\d{2})$/.exec(lesson.id);
    if (match && match[1] === moduleNumber) {
      highest = Math.max(highest, Number(match[2]));
    }
  }
  return `${moduleNumber}-${String(highest + 1).padStart(2, "0")}`;
}

function setYaml(text) {
  $("yaml").value = text;
  state.dirty = true;
}

async function loadCourses() {
  const data = await api("/api/studio/courses");
  state.courses = data.courses || [];
  const select = $("course");
  select.textContent = "";
  for (const course of state.courses) {
    const option = document.createElement("option");
    option.value = course.key;
    option.textContent = course.title || course.key;
    select.append(option);
  }
  if (state.courses.length) {
    await loadModules();
  } else {
    setStatus("No courses registered.", "error");
  }
}

async function loadModules() {
  const key = $("course").value;
  if (!key) return;
  const data = await api(`/api/studio/courses/${encodeURIComponent(key)}/modules`);
  state.modules = data.modules || [];
  const select = $("module");
  select.textContent = "";
  for (const module of state.modules) {
    const option = document.createElement("option");
    option.value = module.slug;
    option.textContent = `${module.number}. ${module.title}`;
    select.append(option);
  }
  if (state.modules.length) {
    await loadModule();
  } else {
    setStatus("No modules found for this course.", "error");
  }
}

async function loadModule() {
  const course = $("course").value;
  const module = $("module").value;
  if (!course || !module) return;
  const data = await api(
    `/api/studio/courses/${encodeURIComponent(course)}/modules/${encodeURIComponent(module)}`
  );
  state.current = data;
  state.lessons = data.lessons || [];
  state.selectedLesson = state.lessons[0]?.id || null;
  state.dirty = false;
  $("yaml").value = data.yaml || "";
  $("path").textContent = data.path || "No overlay file yet";
  renderLessons(state.lessons);
  renderProblems(data.problems || []);
  $("player").src = "about:blank";
  $("open-player").href = "#";
  if (data.exists) {
    setStatus(`Loaded ${data.path}`, "good");
  } else {
    setStatus("No overlay yet. Add a lesson or paste YAML, then save.", "");
  }
}

async function validate() {
  if (!state.current) return;
  try {
    const data = await api("/api/studio/validate", {
      method: "POST",
      body: JSON.stringify({
        course: $("course").value,
        module: $("module").value,
        yaml: $("yaml").value,
      }),
    });
    state.lessons = data.lessons || [];
    renderLessons(state.lessons);
    renderProblems(data.problems || []);
    setStatus(data.ok ? "Valid." : "Validation found problems.", data.ok ? "good" : "error");
    return data.ok;
  } catch (error) {
    renderProblems([error.message]);
    setStatus(error.message, "error");
    return false;
  }
}

async function save() {
  if (!state.current) return;
  try {
    const data = await api(
      `/api/studio/courses/${encodeURIComponent($("course").value)}/modules/${encodeURIComponent($("module").value)}`,
      {
        method: "PUT",
        body: JSON.stringify({ yaml: $("yaml").value }),
      }
    );
    if (!data.ok) {
      renderProblems(data.problems || []);
      setStatus("Not saved. Fix the problems first.", "error");
      return;
    }
    state.lessons = data.lessons || [];
    state.dirty = false;
    renderLessons(state.lessons);
    renderProblems([]);
    $("path").textContent = data.path || $("path").textContent;
    const backup = data.backup ? ` Backup: ${data.backup}.` : "";
    setStatus(`Saved.${backup}`, "good");
  } catch (error) {
    renderProblems([error.message]);
    setStatus(error.message, "error");
  }
}

async function build() {
  try {
    const data = await api("/api/studio/build", {
      method: "POST",
      body: JSON.stringify({ course: $("course").value }),
    });
    const hash = state.selectedLesson ? `#${encodeURIComponent(state.selectedLesson)}` : "";
    const url = `${data.url}${hash}`;
    $("player").src = url;
    $("open-player").href = url;
    setStatus(`Built ${data.title}. Preview updated.`, "good");
  } catch (error) {
    renderProblems([error.message]);
    setStatus(error.message, "error");
  }
}

async function checkCourse() {
  try {
    const data = await api("/api/studio/check", {
      method: "POST",
      body: JSON.stringify({ course: $("course").value }),
    });
    renderProblems(data.problems || []);
    setStatus(data.ok ? "Course check passed." : "Course check found problems.", data.ok ? "good" : "error");
  } catch (error) {
    renderProblems([error.message]);
    setStatus(error.message, "error");
  }
}

function addLesson() {
  const kind = $("kind").value;
  const template = state.templates[kind];
  if (!template) return;
  const id = nextLessonId();
  const block = template
    .replace(/- id: .*/, `- id: ${id}`)
    .split("\n")
    .map((line) => (line ? `  ${line}` : line))
    .join("\n");
  const current = $("yaml").value;
  setYaml(current.trim() ? `${current.replace(/\s+$/, "")}\n\n${block}` : `lessons:\n${block}`);
  state.dirty = true;
  setStatus(`Added a ${kind} starter. Fill in the fields, then validate.`);
}

function exportYaml() {
  const blob = new Blob([$("yaml").value], { type: "text/yaml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${$("course").value}-${$("module").value}.yml`;
  link.click();
  URL.revokeObjectURL(url);
}

async function loadTemplates() {
  const data = await api("/api/studio/templates");
  state.templates = data.templates || {};
  state.kinds = data.kinds || Object.keys(state.templates);
  const select = $("kind");
  select.textContent = "";
  for (const kind of state.kinds) {
    const option = document.createElement("option");
    option.value = kind;
    option.textContent = kind;
    select.append(option);
  }
}

function wire() {
  $("course").addEventListener("change", () => loadModules().catch((error) => setStatus(error.message, "error")));
  $("module").addEventListener("change", () => loadModule().catch((error) => setStatus(error.message, "error")));
  $("validate").addEventListener("click", validate);
  $("save").addEventListener("click", save);
  $("build").addEventListener("click", build);
  $("check").addEventListener("click", checkCourse);
  $("add").addEventListener("click", addLesson);
  $("export").addEventListener("click", exportYaml);
  $("yaml").addEventListener("input", () => { state.dirty = true; });
  $("file").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setYaml(await file.text());
    setStatus(`Imported ${file.name}. Validate before saving.`);
    event.target.value = "";
  });
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      save();
    }
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      validate();
    }
  });
  window.addEventListener("beforeunload", (event) => {
    if (state.dirty) event.preventDefault();
  });
}

async function init() {
  wire();
  if (!token) {
    setStatus("No studio token. Open the URL printed by `lorekeeper studio`.", "error");
    return;
  }
  try {
    await loadTemplates();
    await loadCourses();
  } catch (error) {
    setStatus(error.message, "error");
    renderProblems([error.message]);
  }
}

init();
