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
  sources: [],
  sourcePath: "",
  assets: [],
  history: [],
  redo: [],
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

function selectedIndex() {
  return state.lessons.findIndex((lesson) => lesson.id === state.selectedLesson);
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
    renderInspector();
    return;
  }
  lessons.forEach((lesson, index) => {
    const item = document.createElement("li");
    item.className = "lesson-row";
    if (lesson.id === state.selectedLesson) item.classList.add("selected");

    const select = document.createElement("button");
    select.type = "button";
    select.className = "lesson-select";
    select.innerHTML = `<span class="lesson-title"></span><span class="lesson-meta"></span>`;
    select.querySelector(".lesson-title").textContent = `${lesson.id} · ${lesson.title}`;
    select.querySelector(".lesson-meta").textContent = `${lesson.kind} · ${lesson.xp} XP`;
    select.addEventListener("click", () => {
      state.selectedLesson = lesson.id;
      renderLessons(state.lessons);
      renderInspector();
    });

    const actions = document.createElement("span");
    actions.className = "lesson-actions";
    const controls = [
      ["↑", "Move up", "move", index, index - 1, index === 0],
      ["↓", "Move down", "move", index, index + 1, index === lessons.length - 1],
      ["⧉", "Duplicate lesson", "duplicate", index, null, false],
      ["✕", "Delete lesson", "delete", index, null, false],
    ];
    controls.forEach(([label, title, action, from, to, disabled]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.title = title;
      button.setAttribute("aria-label", title);
      button.disabled = disabled;
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        runLessonAction(action, from, to);
      });
      actions.append(button);
    });

    item.append(select, actions);
    list.append(item);
  });
  renderInspector();
}

function renderInspector() {
  const host = $("lesson-inspector");
  const apply = $("apply-lesson");
  if (!host) return;
  host.textContent = "";
  const index = selectedIndex();
  const lesson = state.lessons[index];
  if (!lesson || !lesson.spec) {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = "Select a lesson to edit its fields.";
    host.append(note);
    if (apply) apply.disabled = true;
    return;
  }
  if (apply) apply.disabled = false;

  const spec = lesson.spec;
  for (const [key, value] of Object.entries(spec)) {
    if (key === "id") continue;
    const label = document.createElement("label");
    label.className = "field";
    const name = document.createElement("span");
    name.textContent = key;
    label.append(name);

    if (key === "kind") {
      const select = document.createElement("select");
      select.dataset.inspectorKey = key;
      for (const kind of state.kinds) {
        const option = document.createElement("option");
        option.value = kind;
        option.textContent = kind;
        if (kind === value) option.selected = true;
        select.append(option);
      }
      label.append(select);
    } else if (typeof value === "number") {
      const input = document.createElement("input");
      input.type = "text";
      input.inputMode = "numeric";
      input.dataset.inspectorKey = key;
      input.dataset.inspectorType = "number";
      input.value = String(value);
      label.append(input);
    } else if (typeof value === "boolean") {
      const input = document.createElement("input");
      input.type = "checkbox";
      input.dataset.inspectorKey = key;
      input.dataset.inspectorType = "boolean";
      input.checked = value;
      label.append(input);
    } else if (
      Array.isArray(value) &&
      value.every((item) => typeof item === "string" || typeof item === "number")
    ) {
      const textarea = document.createElement("textarea");
      textarea.className = "inspector-json";
      textarea.dataset.inspectorKey = key;
      textarea.dataset.inspectorType = "lines";
      textarea.value = value.join("\n");
      label.append(textarea);
    } else if (typeof value === "object" && value !== null) {
      const textarea = document.createElement("textarea");
      textarea.className = "inspector-json";
      textarea.dataset.inspectorKey = key;
      textarea.dataset.inspectorType = "json";
      textarea.value = JSON.stringify(value, null, 2);
      label.append(textarea);
    } else {
      const multiline = typeof value === "string" && (value.includes("\n") || value.length > 90);
      const input = document.createElement( multiline ? "textarea" : "input");
      if (multiline) input.className = "inspector-json";
      else input.type = "text";
      input.dataset.inspectorKey = key;
      input.value = value == null ? "" : String(value);
      label.append(input);
    }
    host.append(label);
  }
}

function inspectorFields() {
  const fields = {};
  for (const field of $("lesson-inspector").querySelectorAll("[data-inspector-key]")) {
    const key = field.dataset.inspectorKey;
    const type = field.dataset.inspectorType;
    if (type === "number") {
      const number = Number(field.value);
      fields[key] = Number.isFinite(number) ? number : field.value;
    } else if (type === "boolean") {
      fields[key] = field.checked;
    } else if (type === "lines") {
      fields[key] = field.value.split("\n").map((line) => line.trim()).filter(Boolean);
    } else if (type === "json") {
      try {
        fields[key] = JSON.parse(field.value);
      } catch {
        throw new Error(`Field "${key}" is not valid JSON.`);
      }
    } else {
      fields[key] = field.value;
    }
  }
  return fields;
}

async function runLessonAction(action, index, target = null, fields = null) {
  if (!state.current) return;
  try {
    const data = await api("/api/studio/lessons", {
      method: "POST",
      body: JSON.stringify({
        course: $("course").value,
        module: $("module").value,
        yaml: $("yaml").value,
        action,
        index,
        target,
        fields,
      }),
    });
    applyEditorResult(data);
    if (action === "delete") {
      state.selectedLesson = state.lessons[Math.min(index, state.lessons.length - 1)]?.id || null;
    } else if (action === "duplicate") {
      state.selectedLesson = state.lessons[index + 1]?.id || state.selectedLesson;
    }
    renderLessons(state.lessons);
    setStatus(data.ok ? "Updated. Save to keep the change." : "Updated, but validation has problems.", data.ok ? "good" : "error");
  } catch (error) {
    renderProblems([error.message]);
    setStatus(error.message, "error");
  }
}

function applyEditorResult(data) {
  snapshot();
  if (typeof data.yaml === "string") $("yaml").value = data.yaml;
  state.lessons = data.lessons || [];
  state.dirty = true;
  renderLessons(state.lessons);
  renderProblems(data.problems || []);
}

async function undoEditor() {
  if (!state.history.length) return;
  state.redo.push($("yaml").value);
  $("yaml").value = state.history.pop();
  state.dirty = true;
  renderHistory();
  await validate();
}

async function redoEditor() {
  if (!state.redo.length) return;
  state.history.push($("yaml").value);
  $("yaml").value = state.redo.pop();
  state.dirty = true;
  renderHistory();
  await validate();
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

function snapshot() {
  state.history.push($("yaml").value);
  if (state.history.length > 40) state.history.shift();
  state.redo = [];
  renderHistory();
}

function renderHistory() {
  const undo = $("undo");
  const redo = $("redo");
  if (undo) undo.disabled = !state.history.length;
  if (redo) redo.disabled = !state.redo.length;
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
  fillPackDefaults();
}

function currentCourse() {
  return state.courses.find((course) => course.key === $("course").value) || null;
}

function fillPackDefaults(reset = false) {
  const course = currentCourse();
  if (!course) return;
  if (reset || !$("pack-id").value) $("pack-id").value = course.slug || course.key;
  if (reset || !$("pack-title").value) $("pack-title").value = course.title || "";
  if (reset || !$("pack-tags").value) $("pack-tags").value = (course.tags || []).join(", ");
  if (reset || !$("pack-pitch").value) $("pack-pitch").value = course.pitch || "";
  if (reset || !$("pack-start").value) $("pack-start").value = course.start || "01-01";
  if (course.level) $("pack-level").value = course.level;
  $("pack-download").hidden = true;
  $("pack-result").textContent = "";
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
  fillPackDefaults();
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
  state.history = [];
  state.redo = [];
  renderHistory();
  $("yaml").value = data.yaml || "";
  $("path").textContent = data.path || "No overlay file yet";
  renderLessons(state.lessons);
  renderProblems(data.problems || []);
  $("new-overlay").hidden = Boolean(data.exists);
  $("player").src = "about:blank";
  $("open-player").href = "#";
  fillPackDefaults();
  await loadSources();
  await loadAssets();
  if (data.exists) {
    setStatus(`Loaded ${data.path}`, "good");
  } else {
    setStatus("No overlay yet. Create one, add a lesson, or paste YAML, then save.", "");
  }
}

async function loadSources() {
  const course = $("course").value;
  const module = $("module").value;
  state.sources = [];
  state.sourcePath = "";
  $("source-file").textContent = "";
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "Choose a file";
  $("source-file").append(blank);
  $("source-headings").textContent = "";
  $("apply-source").disabled = true;
  if (!course || !module) return;
  try {
    const data = await api(
      `/api/studio/courses/${encodeURIComponent(course)}/sources?module=${encodeURIComponent(module)}`
    );
    state.sources = data.sources || [];
    for (const source of state.sources) {
      const option = document.createElement("option");
      option.value = source.path;
      option.textContent = source.path;
      $("source-file").append(option);
    }
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function renderSourceHeadings() {
  const host = $("source-headings");
  host.textContent = "";
  state.sourcePath = $("source-file").value;
  const source = state.sources.find((item) => item.path === state.sourcePath);
  $("apply-source").disabled = !source;
  if (!source) return;
  for (const heading of source.headings) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = heading;
    const text = document.createElement("span");
    text.textContent = heading;
    label.append(input, text);
    host.append(label);
  }
}

async function applySource() {
  const index = selectedIndex();
  const lesson = state.lessons[index];
  if (!lesson) return;
  if (lesson.kind !== "reading") {
    setStatus("Select a reading lesson before applying a source.", "error");
    return;
  }
  const include = [...$("source-headings").querySelectorAll("input:checked")].map((input) => input.value);
  await runLessonAction("update", index, null, {
    source: $("source-file").value,
    include,
  });
  setStatus("Reading source updated. Save to keep the change.", "good");
}

async function loadAssets() {
  const course = $("course").value;
  state.assets = [];
  if (!course) return renderAssets();
  try {
    const data = await api(`/api/studio/courses/${encodeURIComponent(course)}/assets`);
    state.assets = data.assets || [];
  } catch (error) {
    setStatus(error.message, "error");
  }
  renderAssets();
}

function renderAssets() {
  const host = $("asset-list");
  host.textContent = "";
  if (!state.assets.length) {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = "No images yet.";
    host.append(note);
    return;
  }
  for (const asset of state.assets) {
    const row = document.createElement("div");
    row.className = "asset-row";
    const name = document.createElement("code");
    name.textContent = `assets/${asset.name}`;
    const use = document.createElement("button");
    use.type = "button";
    use.className = "ghost";
    use.textContent = "Copy path";
    use.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(`assets/${asset.name}`);
        setStatus(`Copied assets/${asset.name}.`, "good");
      } catch {
        setStatus(`Use assets/${asset.name} in lesson HTML.`, "");
      }
    });
    row.append(name, use);
    host.append(row);
  }
}

async function uploadAsset() {
  const file = $("asset-file").files?.[0];
  if (!file) return;
  const data = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read the image."));
    reader.readAsDataURL(file);
  });
  try {
    await api(`/api/studio/courses/${encodeURIComponent($("course").value)}/assets`, {
      method: "POST",
      body: JSON.stringify({ name: file.name, data }),
    });
    $("asset-file").value = "";
    $("asset-upload").disabled = true;
    await loadAssets();
    setStatus(`Uploaded ${file.name}. Use assets/${file.name} in lesson HTML.`, "good");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function createOverlay() {
  try {
    const data = await api(
      `/api/studio/courses/${encodeURIComponent($("course").value)}/modules/${encodeURIComponent($("module").value)}`,
      { method: "POST", body: JSON.stringify({ action: "init" }) }
    );
    if (!data.ok) {
      renderProblems(data.problems || []);
      setStatus("Could not create the overlay.", "error");
      return;
    }
    $("yaml").value = data.yaml || $("yaml").value;
    state.lessons = data.lessons || [];
    state.dirty = false;
    $("new-overlay").hidden = true;
    renderLessons(state.lessons);
    renderProblems([]);
    setStatus("Overlay created from the module defaults.", "good");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function buildPack() {
  if (state.dirty && !(await save())) return;
  try {
    const data = await api("/api/studio/pack", {
      method: "POST",
      body: JSON.stringify({
        course: $("course").value,
        id: $("pack-id").value,
        title: $("pack-title").value,
        author: $("pack-author").value,
        licence: $("pack-licence").value,
        tags: $("pack-tags").value,
        level: $("pack-level").value,
        pitch: $("pack-pitch").value,
        start: $("pack-start").value,
      }),
    });
    if (!data.ok) {
      renderProblems(data.problems || []);
      setStatus("Pack not built. Complete the manifest.", "error");
      return;
    }
    const link = $("pack-download");
    link.href = data.url;
    link.download = data.filename;
    link.hidden = false;
    $("pack-result").textContent = `Built ${data.path} (${Math.round(data.size / 1024)} KB).`;
    setStatus("Pack built. Download it or submit it to the queue.", "good");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function registerCourse() {
  try {
    const data = await api("/api/studio/courses", {
      method: "POST",
      body: JSON.stringify({
        title: $("reg-title").value,
        key: $("reg-key").value,
        slug: $("reg-slug").value,
        code: $("reg-code").value,
        root: $("reg-root").value,
        tags: $("reg-tags").value,
      }),
    });
    setStatus(`Registered ${data.key}. Reloading courses.`, "good");
    await loadCourses();
  } catch (error) {
    setStatus(error.message, "error");
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
      return false;
    }
    state.lessons = data.lessons || [];
    state.dirty = false;
    renderLessons(state.lessons);
    renderProblems([]);
    $("path").textContent = data.path || $("path").textContent;
    const backup = data.backup ? ` Backup: ${data.backup}.` : "";
    setStatus(`Saved.${backup}`, "good");
    return true;
  } catch (error) {
    renderProblems([error.message]);
    setStatus(error.message, "error");
    return false;
  }
}

async function build() {
  if (state.dirty && !(await save())) return;
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
  snapshot();
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
  $("course").addEventListener("change", () => {
    fillPackDefaults(true);
    loadModules().catch((error) => setStatus(error.message, "error"));
  });
  $("module").addEventListener("change", () => loadModule().catch((error) => setStatus(error.message, "error")));
  $("validate").addEventListener("click", validate);
  $("undo").addEventListener("click", undoEditor);
  $("redo").addEventListener("click", redoEditor);
  $("save").addEventListener("click", save);
  $("build").addEventListener("click", build);
  $("check").addEventListener("click", checkCourse);
  $("add").addEventListener("click", addLesson);
  $("export").addEventListener("click", exportYaml);
  $("new-overlay").addEventListener("click", createOverlay);
  $("apply-lesson").addEventListener("click", () => {
    const index = selectedIndex();
    if (index < 0) return;
    try {
      runLessonAction("update", index, null, inspectorFields());
    } catch (error) {
      setStatus(error.message, "error");
    }
  });
  $("source-file").addEventListener("change", renderSourceHeadings);
  $("apply-source").addEventListener("click", applySource);
  $("asset-file").addEventListener("change", () => {
    $("asset-upload").disabled = !$("asset-file").files?.length;
  });
  $("asset-upload").addEventListener("click", uploadAsset);
  $("pack-build").addEventListener("click", buildPack);
  $("reg-submit").addEventListener("click", registerCourse);
  $("yaml").addEventListener("input", () => { state.dirty = true; });

  $("file").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    snapshot();
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
