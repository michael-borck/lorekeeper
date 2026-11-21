# Lorekeeper

<p align="center">
  <img src="player/art/quest/hero.webp" alt="Lorekeeper" width="640">
</p>

Story-driven courses for your personal learning path.

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

## Static site and GitHub Pages

Build a standalone site and serve it locally:

```bash
python3 -m lorekeeper site --out _site --cname lorekeeper.borck.education
python3 -m http.server --directory _site 8000
# open http://127.0.0.1:8000/
```

`scripts/deploy-site.sh` builds `_site/` and pushes it to the public
`michael-borck/lorekeeper-site` repository. GitHub Pages serves that repo, while
the source and private course repos stay private. The live test URL is
<https://michael-borck.github.io/lorekeeper-site/>.

The site contains only built player files and course JSON. The custom domain is
`lorekeeper.borck.education`; point a Cloudflare `CNAME` for `lorekeeper` at
`michael-borck.github.io` with the proxy off, then attach the domain in GitHub
Pages.

## Wayfinder and world map

The **world map** (`?view=world`) is a Tolkien-style parchment map of the realm.
Each narrator rules a region (Captain Vey's Northern Ramparts for security, Cog's
Clockwork Heights for AI, Tinker's Vale for programming, Hale's Keep for systems,
the Harbour Reach for networks, Ashwood for teaching, the Far Shore for
reference, and Orin's Archive at the centre), and every course is a place in its
guide's region. Courses in your library are bright and labelled; packs in the
store and built-in courses you have not added appear greyed out as unexplored,
and clicking one finds it in the store or adds it to your library. On phones and
in Study mode the map becomes a list grouped by region.

**Find my trail** asks four questions (goal, experience, a familiar situation and
a preferred start) and plots a route of two to four courses across the realm,
starting with one you already have where possible. Each stop's goal is to clear
that course's first chapter. The trail is drawn on the world map as a dashed
route and shown in a collapsible **Your trail** panel in the sidebar. Finishing
every stop earns the Pathfinder moment. It is a recommendation, not a gate, and
nothing leaves the device. Older single-course trails migrate automatically.

The region for a course comes from its narrator: the author's `narrator` field,
or `PACK_NARRATOR` in `lorekeeper/store.py` for store packs, then the tags. The
map art was made with limn (`scripts/quest_art.py`, job `world`).

## Library and store

The library starts empty. Use **Browse packs** to install a signed pack, or
**Manage library** to show or hide built-in courses, restore the starter kit,
or remove a local pack and its progress. Pack and lesson progress are stored
in IndexedDB; legacy `localStorage` packs and progress migrate on first load.
Exercise drafts remain in `localStorage` and are included in progress export.

The store supports search, category filters, level, installed-only and sort.
Packs are hash- and signature-verified before install.

## Artwork

Pack thumbnails and course covers use a curated subset of the SwipeVerse art
library. Quest mode adds narrator portraits, a library hero and a map backdrop
generated with [limn](https://pypi.org/project/limn/) using the SwipeVerse pixel
recipe (SDXL plus the `pixel-art-xl` LoRA, fixed seeds). Regenerate or extend them
with `scripts/quest_art.py`; candidates and picks stay in the gitignored `art/`
folder and only processed WebP ships in `player/art/quest/`.

## Journey and tutor

**Journey** shows courses started and completed, recent lessons, achievements
and a suggested next course. **AI tutor** is optional: configure a local Ollama
server, a shared endpoint, or an OpenAI-compatible API in the tutor panel. The
API key is kept for the current tab only. Nothing is sent until you press Send.

## Install and offline

Lorekeeper is a PWA. Open the player and use the browser's **Install** action if
you want an app icon and a standalone window. The service worker caches the
player shell, vendored runtimes and visited course content.

Course JSON is network-first, so updates arrive when online and the last version
works offline. The PWA adds no accounts, analytics, push notifications or
permission prompts. See [`docs/distribution.md`](docs/distribution.md) for the
Tauri and pack-store decisions.

## Design

- A course is a story. Modules are chapters, lessons are scenes, exercises are
  the things the learner actually does.
- Learner-facing titles are thematic. They carry the theme, not the source code.
- Lorekeeper compiles from source course repos and never writes into them.
  That is an engineering constraint, not learner-facing copy.
- Internal keys, codes and paths stay in metadata for provenance. They do not
  appear in the player.
- Art direction is separate from content. Two modes ship today: Quest and
  Study. The learner picks one; content never changes.

## Modes

| Mode | Purpose | Look |
|---|---|---|
| Quest (default) | Fun, game-like progress | 16-bit RPG: night-sky interface, parchment lesson pages, gold dialogue frames, narrator portraits, levels and a course map |
| Study | Long reading, projection, accessibility | Calm dark interface, wider line spacing, narrower reading column, no banners, no animation |

Switch modes from **Menu** in the sidebar. The choice is saved locally, and the
old skin names migrate automatically (Ink becomes Study; Pixel and Storybook
become Quest).

Quest mode turns the sidebar into a quest log: a player card with level, XP to
the next level and a daily streak, then chapters as a path with verb icons for
each lesson (Read, Quiz, Build, Sort, Spot, Decide and so on). Each lesson opens
as a numbered scene with the course art as a banner and a narrator chosen from
the pack's topic. Finishing a scene stamps it, finishing a chapter unlocks the
next one, and levelling up gets its own moment. The **Course map** shows chapters
as stops on a path. The picker leads with **Continue your quest** and the next
scene. Quest sound is optional and off by default.

Study mode keeps the same structure and wording in plain terms (chapters and
lessons) and stays quiet. All motion respects `prefers-reduced-motion`.

### Narrators

Eight guides narrate Quest mode, each with their own voice: Orin the Archivist,
Captain Vey (security), Cog (AI), Wren the Courier (networks), Tink
(programming), Master Hale (systems), Mentor Ash (teaching) and Pip the
Cartographer (reference). The guide for a course is chosen in this order:

1. the learner's choice under **Menu, Guide**;
2. the author's `narrator` field in the course registry or pack;
3. the course tags.

Lines come from `player/narrators.json` (about 30 KB, cached offline with the
rest of the app). Each guide has voiced lines for every lesson type, mixed with a
set of plain standard lines, and responds to the moment: the start of a course
or chapter, the last scene of a chapter or course, coming back after three or
more days, a wrong answer, and a level up. An author can replace the line for a
single lesson with an optional `narration` field in the overlay.

## How it works

```
courses/*.yaml                registry: which course sources may be read
content/<course>/modules/...  overlays: interactive lessons (you write these)
demo-course/                  Field Kit source: the widget test bench
lorekeeper/                   compiler and CLI (Python, PyYAML + Markdown)
player/                       player, widgets, art and vendored runtimes
scripts/compile-ink.mjs       compile an Ink source into story JSON
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
| Ship It: Web Craft with an AI Partner | `?course=ship-it` | 12 chapters, 56 lessons |
| Signal & Noise: An Enterprise Systems Field Guide | `?course=signal-and-noise` | 12 chapters, 47 lessons |
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
narrator: artificer          # optional Quest guide; omit to pick from tags
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
- Any lesson can set `narration: "A line for the guide to say."` (up to 400
  characters) to replace the narrator's default line for that scene.
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

## Authoring studio

The landing page has a short **Authors and teachers** path: clone the engine,
install it with pip, and run the local studio. For a browser-based editor, run:

```bash
python3 -m lorekeeper studio
```

It lists the courses and modules, edits overlays with YAML and a field
inspector, validates against the same compiler, checks duplicate lesson IDs
across the course, saves with a backup under `build/studio-backups/`, previews
through the real player, manages reading sources and images, and exports a pack
with a complete manifest. It is local-only, bound to `127.0.0.1`, and protected
by a per-run token. See [`docs/authoring-studio.md`](docs/authoring-studio.md).

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
| `story` | Ink interactive fiction | Plays a branching conversation | Client interviews, incidents, judgement |

The Field Kit course is the living reference. It has one lesson per widget in
`content/field-kit/modules/01-workbench/lessons.yml`.

Exercise tests run in a hidden sandboxed iframe with a nonce CSP. They can read
the rendered exercise, but they cannot reach the parent page, local storage or
the network. The preview remains separate and blocks scripts. This is what makes
third-party packs defensible, along with signing.

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
| `story` | `story` path under `content/<course>/`, optional `start`, `intro`, `debrief` |

The viva widget is deliberately deterministic. It does not call an LLM. It checks
whether an answer contains the signals you define, shows a strong answer, and
asks the learner to self-rate against a rubric. The signal and reflection
patterns borrow from Study Buddy's Socratic and Feynman modes, and the
self-assessment structure borrows from Talk Buddy's session analysis. A real
Socratic chat can be added later as an optional service.

The SQL widget vendors `sql.js` (MIT) in `player/vendor/`. It runs real SQLite in
the browser, so the learner can test a query instead of reading about one.

The story widget vendors `inkjs` (MIT) in `player/vendor/`. Compiled Ink JSON
lives under `content/<course>/stories/` and is copied into
`build/<course>/stories/` at compile time. Keep the editable `.ink` source next
to the JSON and recompile it with:

```bash
node scripts/compile-ink.mjs content/<course>/stories/name.ink content/<course>/stories/name.json
```

The first stories are the Ship It client interview and launch week, and the
Signal & Noise 3AM page.

## Achievements

The player keeps a local badge case. No account and no server are needed. The
twelve achievements cover first steps, checkpoints, exercises, stories, five and
ten different lesson formats, a completed chapter, a completed course, 100 and
500 XP, and three- and seven-day streaks.

Badges are derived from the same progress record as the lessons. The dialog shows
locked badges with their progress, and each new badge raises a toast. Reset
progress also clears the badge case.

## Progress backup

Progress and badges live in IndexedDB. Exercise drafts and the chosen mode live
in `localStorage`. The **Progress** dialog exports them together as one JSON file
and imports a file with **Merge** or **Replace**. Merge unions completed lessons, activity dates,
badges and missing drafts; Replace restores the file exactly.

Clearing browser storage erases the local copy. Lorekeeper asks the browser for
persistent storage where the API exists, but a manual clear still wins. Export a
backup before clearing site data or moving to another laptop.

## Packs

A pack is one course plus its compiled stories, in a single JSON file:

```bash
python3 -m lorekeeper pack ship-it
# build/packs/ship-it.json
```

Build a pack from a Quarto book:

```bash
python3 -m lorekeeper pack-book /path/to/book \
  --id assume-breach --part 1 --tags security,risk,incident
```

Parts become modules and chapters become reading lessons. Markdown images are
stripped for now, and the book's CC BY licence is carried into the pack manifest.

Package a unit folder directly, without registering it as a built-in course:

```bash
python3 -m lorekeeper pack --root ../isys2012-information-security \
  --id information-security --title "Information Security: A Field Guide" \
  --tags security,risk,operations --theme pixel
```

Import it from the course picker. Local packs live in IndexedDB, appear with a
**Local pack** tag, and can be removed without touching the built-in courses.
Pack assets are embedded in the pack file. Progress and drafts stay separate
from the pack file.

Packs can contain exercise test code. Only import packs you trust.

### Pack store

`python3 -m lorekeeper store` builds a static catalogue in `store/`:

```text
store/catalog.json
store/packs/pocket-incidents.json
store/README.md
```

Public submissions go through the review queue at
<https://github.com/michael-borck/lorekeeper-packs>. The store ships
**Pocket Incidents: The 3AM Page**, a short incident-response course,
**Information Security: A Field Guide**, **Audit and Control: A Field Guide**,
**Assume Breach: A First Course in Defensive Security**, **Speak Software:
Programming at the Natural-Language Layer**, **Build Web, Guide AI:
Business Web Development with AI**, **Frame the System, Guide the AI:
Systems Analysis and Design in the AI Era**, and **Follow the Trace, Prove the
Case: Digital Forensics in Practice**, and **The Human Edge: Using AI with
Judgement**, **Test the Claim, Rate the Control: A Tessera Audit Workbook**, and
**Substantiate, Don't Assume: Why the Auditor's Opinion Matters More Than Ever
in the Age of AI**, and **Conversation, Not Delegation: How to Think With AI,
Not Just Use It**, and **Prove, Don't Persuade: Why Proof Beats the Demo in
Applied AI**, and **Build AI, Understand AI: How Today's LLM Systems Actually
Work, in Small Readable Pieces**, and **Break with Permission: Ethical Hacking
in Practice**, and **Follow the Packet: An Enterprise Network Field Guide**.
**SimpleBot: A Small Wrapper, a Real Project**, and **Build It, Teach It:
Hands-on AI Projects for the Classroom**. The store also includes the full Python track, *The Great Silence*,
*One Calculator, Three Paradigms* and *Simulate It, Understand It*.
The player fetches `store/catalog.json`,
checks the pack SHA-256 and Ed25519 signature, validates the pack and stores it
locally.

### Pack signing

Generate a signing key outside the repository:

```bash
python3 -m lorekeeper keygen --trusted player/trusted-keys.js
```

The private key lives at `~/.lorekeeper/lorekeeper-signing.pem` (mode 600) and
must never be committed. The public key is pinned in `player/trusted-keys.js`.
Build and sign the store with:

```bash
python3 -m lorekeeper store --out store --key ~/.lorekeeper/lorekeeper-signing.pem
```

The deploy script requires the key and signs every published pack. Verify the
published files without the private key:

```bash
python3 -m lorekeeper verify-store --store store --trusted player/trusted-keys.js
```

The signature proves authorship and integrity for a known key. Exercise tests
are also sandboxed, but a public catalogue still needs review. The policy and
key-rotation procedure are in [`docs/store-policy.md`](docs/store-policy.md).

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
| Ink story with `inkjs` | Working |
| Three Ink stories | Working |
| Authoring studio (`lorekeeper studio`) | Working |
| Studio field inspector, CRUD, sources, images, pack export | Working |
| Badges and streaks | Working |
| XP, progress, IndexedDB | Working |
| Ship It course | Complete |
| Signal & Noise course | Complete, 12 chapters curated |
| Field Kit demo | Complete |
| Server-side sandbox | Not built |
| LLM-backed Socratic tutor | Not built |
| Pack build and local import | Working |
| Static pack catalogue and sample pack | Working |
| Ed25519 pack signing | Working |
| Store verification and key rotation | Working |
| Sandboxed exercise tests | Working |
| Tauri desktop shell | Deferred |
| LMS grade export | Not built |
| Quest and Study modes | Working |
| Levels, streaks, completion moments, course map | Working |
| Theme illustrations and motion | Working |
| Course-specific emblems | Working |
| PWA install and offline shell | Working |
| Progress export and import | Working |
| Static site build and GitHub Pages deploy | Working |
| Quarto book packs (`pack-book`) | Working |
| Wayfinder onboarding and trails | Working |

## Roadmap

1. Open a public pack submission flow using the review policy.
2. Add more real course overlays and Ink stories.
3. Add per-course narrator art and course-specific scenes.
4. Optional: a Tauri shell if native labs or offline pack management need it.
5. Optional: a container runner for real shell exercises.
6. Optional: an LLM-backed Socratic tutor for open viva answers.
7. Optional: export completion to an LMS.

## Tests

```bash
python3 -m pytest -q
ruff check lorekeeper tests
```

The full suite compiles every registered course, checks overlay validity,
asserts the source files are byte-identical before and after the build, and
scans learner-facing output for source codes or institutional names.

CI runs ruff, checks and builds the bundled Field Kit course, runs the
source-independent tests, and runs the studio UI tests in Chromium. The full
course suite and the site build need the sibling course repositories, so they
stay a local check.
