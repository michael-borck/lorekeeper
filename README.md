# Lorekeeper

Story-driven courses for information systems.

Lorekeeper turns a course source tree into short readings, checkpoints and
hands-on challenges, then serves them in a browser player with XP, progress and
completion. It is a practice layer, not the primary LMS: optional, playful, and
safe to run alongside whatever teaching platform a course already uses.

## Quick start

```bash
cd lorekeeper
pip install -e .            # optional: gives you the `lorekeeper` command
python3 -m lorekeeper courses
python3 -m lorekeeper check all
python3 -m lorekeeper build all
python3 -m lorekeeper serve
```

The player opens at <http://127.0.0.1:8000/player/>. No Node build step is
required.

If you prefer a plain server:

```bash
python3 -m http.server 8000
# then open http://127.0.0.1:8000/player/
```

## Design

- A course is a story. Modules are chapters, lessons are scenes, exercises are
  the things the learner actually does.
- Learner-facing titles are thematic. They carry the theme, not the source code.
- Source course repos are read-only. Lorekeeper compiles from them and never
  writes into them.
- Internal keys, codes and paths stay in metadata for provenance. They do not
  appear in the player.
- Art direction is separate from content. The same lesson can later be skinned
  as pixel art, animated illustration, or something else entirely.

## How it works

```
courses/*.yaml                registry: which course sources may be read
content/<course>/modules/...  overlays: interactive lessons (you write these)
demo-course/                  Field Kit source: the widget test bench
lorekeeper/                   compiler and CLI (Python, PyYAML + Markdown)
player/                       player, widgets and vendored sql.js
build/                        generated course JSON (gitignored)
```

Compile pipeline:

1. `discover.py` walks `<source>/modules/NN-slug/` and reads the module title.
2. `compile.py` loads an overlay if one exists, otherwise derives reading
   lessons from `overview.qmd` and `in-class/activity-01.qmd`.
3. `parse.py` strips Quarto shortcodes, splits on `##` headings, renders
   Markdown to HTML, and filters by the `include` list.
4. Replacements map source-specific codes to learner-facing wording.
5. The result is `build/<course>/course.json` plus `build/index.json`.

The compiler refuses to write inside a source repo, and a test hashes the source
tree before and after a build.

## Courses

| Course | Public path | Status |
|---|---|---|
| Ship It: Web Craft with an AI Partner | `?course=ship-it` | 12 chapters, 55 lessons |
| Signal & Noise: An Enterprise Systems Field Guide | `?course=signal-and-noise` | 1 curated chapter, the rest derived |
| Field Kit: The Lorekeeper Workbench | `?course=field-kit` | 10 lessons, one of every widget |

A course can be as small as a set of readings and checkpoints. The engine does
not require a full build.

## Authoring a course

A registry entry gives the engine a source and a learner-facing identity:

```yaml
key: web-craft
code: INTERNAL-CODE          # provenance only
slug: ship-it                # public path and build folder
title: "Ship It: Web Craft with an AI Partner"
root: ../../source-course
replacements:
  "INTERNAL-CODE": "this course"
  "NEXT-CODE": "the next course"
```

`key`, `code` and `root` are internal. `slug`, `title` and `replacements` shape
what a learner sees. Replacements apply to module titles, reading HTML, prompts and
other learner-facing strings.

Create `content/<key>/modules/<slug>/lessons.yml`. The source repo is untouched.

```yaml
lessons:
  - id: 01-01
    kind: reading
    title: What a website actually is
    source: overview.qmd
    include:
      - The question
      - Learning objectives

  - id: 01-02
    kind: checkpoint
    title: "Checkpoint: the evidence trio"
    questions:
      - prompt: Which three files record the work?
        options: ["SPEC, DECISIONS, CRITIQUE", "README, LICENSE, index.html"]
        answer: 0
        explanation: One file for intent, one for overrides, one for reflection.

  - id: 01-03
    kind: exercise
    title: Build the home page skeleton
    language: html
    prompt: |
      Add one `h1`, a `nav` with three links, and a booking link.
    starter: |
      <!doctype html>
      <html lang="en"><body></body></html>
    tests:
      - name: One h1
        script: |
          assert(doc.querySelectorAll('h1').length === 1, 'Use exactly one <h1>.')
    hints:
      - Put the links inside <nav>.
```

Notes:

- `id` values must be unique across the course.
- `include` matches headings exactly (case-insensitive). A missing heading fails
  the build instead of silently dropping content.
- `kind` is `reading`, `checkpoint` or `exercise`.
- Exercise tests are JavaScript. HTML exercises receive `doc` (the preview
  iframe document); `language: text` exercises receive `text` (the learner's
  answer) and render no preview. `language: js` exercises use `html` as the page
  scaffold and `mock` (`{status, body}`) as a fake `fetch` response; the student
  code runs in the preview iframe. Helpers: `assert(condition, message)` and
  `assertEqual(actual, expected, message)`.
- Add `viewport: { width: 375, height: 667 }` to an exercise to render and test
  at a phone size.
- HTML previews are sandboxed without script execution. JavaScript exercises
  opt into scripts inside the same sandbox. Both are for staff-authored content.
- Overlays only add lessons. To change teaching content, edit the source course.

## Lesson types

| Type | Preview | What the learner does | Good for |
|---|---|---|---|
| Reading | Rendered HTML | Reads | Concepts, procedures, context |
| Checkpoint | Multiple choice | Answers and checks | Recall and judgement |
| `language: text` | None | Writes prose | Specs, memos, reviews, manifests |
| `language: html` | Sandboxed page | Edits and runs tests | Markup, semantics, responsive layout |
| `language: js` | Sandboxed page with mocked `fetch` | Edits and runs tests | Fetch, state, rendering, data shapes |
| `order` | Sortable list | Puts steps in order | Incident response, protocols, SDLC |
| `fill` | Inline blanks | Completes a passage | Commands, SQL clauses, ARIA, config |
| `hotspot` | Clickable diagram | Finds the targets | Exposed endpoints, missing landmarks |
| `review` | Code lines | Selects the bad lines | Diff review, weakened checks, audits |
| `scenario` | Choice cards | Chooses and sees consequences | Vendor choice, trade-offs, escalation |
| `calibration` | Two artefacts | Chooses the stronger one and explains | Critique, ranking, judgement |
| `viva` | Text prompts | Answers, compares, self-rates | Viva practice, defence, reflection |
| `api` | Endpoint explorer | Sends requests and reads JSON | REST shapes, exposure, data models |
| `sql` | Real SQLite sandbox | Writes and runs a query | Data, joins, filtering, reporting |
| `terminal` | Scripted terminal | Types commands to meet goals | Diagnostics, shell sequences, labs |

The Field Kit course is the living reference. It has one lesson per widget in
`content/field-kit/modules/01-workbench/lessons.yml`.

Widget fields at a glance:

| Kind | Required fields |
|---|---|
| `order` | `prompt`, `items`, `explanation` |
| `fill` | `prompt`, `passage` with `[[1]]` markers, `blanks` |
| `hotspot` | `prompt`, `markup`, `targets` with `selector`, `label`, `feedback` |
| `review` | `prompt`, `lines` with `bad: true`, `explanation` |
| `scenario` | `prompt`, two or more `options`, `debrief` |
| `calibration` | `prompt`, `a`, `b`, `better`, `rationale` |
| `viva` | `context`, `questions` with `signals`, `rubric` |
| `api` | `prompt`, `endpoints`, `questions` |
| `sql` | `prompt`, `task`, `schema`, `seed`, `solution` |
| `terminal` | `prompt`, `goals`, `commands` with `pattern` and `completes` |

The viva widget is deliberately deterministic. It does not call an LLM. It checks
whether an answer contains the signals you define, shows a strong answer, and
asks the learner to self-rate against a rubric. The signal and reflection
patterns borrow from Study Buddy's Socratic and Feynman modes, and the
self-assessment structure borrows from Talk Buddy's session analysis. A real
Socratic chat can be added later as an optional service.

The SQL widget vendors `sql.js` (MIT) in `player/vendor/`. It runs real SQLite in
the browser, so the learner can test a query instead of reading about one.

## What is built

| Area | Status |
|---|---|
| Compiler, registry, overlay format | Working |
| Reading lessons from `.qmd` | Working |
| Multiple-choice checkpoints | Working |
| HTML/CSS exercises with DOM tests | Working |
| Text exercises with pattern checks | Working |
| JavaScript exercises with mocked fetch | Working |
| Order, fill, hotspot, review | Working |
| Scenario and calibration | Working |
| Viva simulator with signals and rubric | Working |
| API explorer | Working |
| SQL sandbox (sql.js) | Working |
| Scripted terminal | Working |
| XP, progress, localStorage | Working |
| Ship It course | Complete |
| Signal & Noise course | In progress |
| Field Kit demo | Complete |
| Ink branching story | Not built |
| Server-side sandbox | Not built |
| LLM-backed Socratic tutor | Not built |
| LMS grade export | Not built |
| Pixel-art or animated skin | Not built |

## Roadmap

1. Add real course overlays for the new widgets, starting with the Module 04
   gaming diff and the Signal & Noise networking sequence.
2. Add an Ink story block for branching client and incident scenarios.
3. Add a badge layer for streaks, chapters and course completion.
4. Choose the art direction and add a skin without touching lesson content.
5. Optional: a container runner for real shell exercises, behind a separate
   service.
6. Optional: an LLM-backed Socratic tutor for open viva answers.
7. Optional: export completion to an LMS.

## Tests

```bash
python3 -m pytest -q
ruff check lorekeeper tests
```

The suite compiles every registered course into a temporary directory, checks
overlay validity, asserts the source files are byte-identical before and after
the build, and scans learner-facing output for source codes or institutional
names.
