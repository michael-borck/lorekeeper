# Lorekeeper authoring studio

Status: v0.2 implemented as a local-only studio with pack export.

## Why

Lorekeeper's overlay format is rich. A module can contain readings, checkpoints,
exercises, and more than a dozen interactive widgets. Hand-editing
`content/<course>/modules/<slug>/lessons.yml` works for the engine author, but it
is error-prone for anyone else.

The authoring studio is a local workbench for that YAML. It is built into
Lorekeeper rather than shipped as a separate app because the compiler, validator,
player, and widget renderers already live here.

## Design choices

- Local-only. The studio binds to `127.0.0.1` and requires a random token.
- Separate command. `lorekeeper studio` is not the learner `serve` command.
- Same format. The studio reads and writes the existing overlay YAML.
- No second runtime. The browser UI is plain HTML, CSS, and JavaScript.
- No hidden writes. The studio writes only under `content/`.
- Validation before save. The compiler's lesson normalisers are the source of
  truth.
- Backups. The previous file is copied under `build/studio-backups/` before a
  write.
- Preview through the real player. The studio builds the course and opens the
  existing player.

## Usage

```bash
python3 -m lorekeeper studio
# opens http://127.0.0.1:8765/studio/?token=...
```

Options:

```bash
python3 -m lorekeeper studio --port 8765 --no-open
```

## What v0.2 does

- Lists registered courses and their modules.
- Registers a new source course from a local folder.
- Loads an existing overlay or creates one from a module's default readings.
- Shows the YAML editor with the parsed lesson list.
- Validates the overlay against the current compiler and checks duplicate lesson
  IDs across the whole course before saving.
- Saves valid YAML atomically and creates a backup before saving.
- Appends a starter lesson for every supported kind.
- Duplicates, deletes and reorders lessons.
- Provides a field inspector for every top-level lesson field. Scalars, booleans,
  number fields, string lists and nested JSON are editable without hand-writing
  the surrounding YAML.
- Lists `.qmd` files and headings for reading lessons, then applies the selected
  source and include headings to the current reading.
- Uploads course images, lists them and makes the `assets/<name>` path easy to
  copy. Assets are copied into course builds and exported inside packs.
- Undo and redo for editor changes.
- Imports and exports YAML.
- Builds the course and opens the player at the selected lesson.
- Runs the full course check.
- Builds a signed-ready pack with manifest fields for id, title, author, licence,
  tags, level, pitch and start lesson, with a download link and a submission link.

## What v0.2 still does not do

- No visual lesson graph.
- No multi-user editing or accounts.
- No write access to source course repositories. Module folders and source files
  remain owned by the source repository; the studio only creates overlays under
  `content/`.
- No arbitrary binary asset types. Images are limited to PNG, JPEG, GIF, WebP and
  AVIF because SVG can carry active content.

## API

The studio uses a small local JSON API. Every request needs the token in
`X-Studio-Token` or the `token` query parameter.

```
GET  /api/studio/courses
POST /api/studio/courses                    register a source course
GET  /api/studio/courses/<key>/modules
GET  /api/studio/courses/<key>/modules/<slug>
PUT  /api/studio/courses/<key>/modules/<slug>
POST /api/studio/courses/<key>/modules/<slug>  create an overlay from defaults
GET  /api/studio/courses/<key>/sources?module=<slug>
GET  /api/studio/courses/<key>/assets
POST /api/studio/courses/<key>/assets       upload an image
POST /api/studio/lessons                    duplicate, delete, move or update
POST /api/studio/validate
POST /api/studio/build
POST /api/studio/check
POST /api/studio/pack                       build a portable pack
GET  /api/studio/templates
```

`PUT` and `POST /api/studio/validate` accept:

```json
{
  "course": "field-kit",
  "module": "01-workbench",
  "yaml": "lessons:\n  - id: 01-01\n..."
}
```

## Validation

The studio reuses `_lesson_from_spec` from the compiler. That means the studio
and the build agree on what a valid lesson is. The studio adds checks for:

- YAML syntax.
- A top-level mapping.
- A `lessons` list.
- Duplicate lesson IDs inside the module.
- Missing overlays or unreadable source files.

The next step is a declarative schema for every lesson kind, exported as JSON
Schema. That will let the studio render generated forms and give field-level
errors instead of normaliser messages.

## Security

- Bind to `127.0.0.1` only.
- Random token per run.
- Static files are limited to the studio UI, player, build output, store and
  course asset folders. Source and registry files are not served.
- Reject unknown courses and modules.
- Resolve paths and verify they stay under `content/`.
- Parse YAML with `yaml.safe_load`.
- Write atomically with `os.replace`.
- Keep a backup under `build/studio-backups/`.
- Never write inside the source course repository.

## Next steps

1. Add a declarative schema per lesson kind so nested lists of objects can be
   edited as repeatable forms rather than JSON.
2. Add a visual lesson graph and drag-and-drop reorder.
3. Add per-course history beyond the current session undo stack.
4. Add a standalone wrapper later only if non-technical authors need one.
