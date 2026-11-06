# Lorekeeper authoring studio

Status: v0.1 implemented as a local-only studio.

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

## What v0.1 does

- Lists registered courses and their modules.
- Loads an existing overlay or starts a new one.
- Shows the YAML editor with the parsed lesson list.
- Validates the overlay against the current compiler.
- Saves valid YAML atomically.
- Creates a backup before saving.
- Appends a starter lesson for a selected kind.
- Imports and exports YAML.
- Builds the course and opens the player at the selected lesson.
- Runs the full course check.

## What v0.1 does not do

- No form editor for every widget field yet.
- No visual lesson graph.
- No asset manager.
- No source-heading picker for readings.
- No multi-user editing or accounts.
- No write access to source course repositories.

## API

The studio uses a small local JSON API. Every request needs the token in
`X-Studio-Token` or the `token` query parameter.

```
GET  /api/studio/courses
GET  /api/studio/courses/<key>/modules
GET  /api/studio/courses/<key>/modules/<slug>
PUT  /api/studio/courses/<key>/modules/<slug>
POST /api/studio/validate
POST /api/studio/build
POST /api/studio/check
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
- Reject unknown courses and modules.
- Resolve paths and verify they stay under `content/`.
- Parse YAML with `yaml.safe_load`.
- Write atomically with `os.replace`.
- Keep a backup under `build/studio-backups/`.
- Never write inside the source course repository.

## Next steps

1. Add a declarative schema per lesson kind and field-level errors.
2. Add form controls for `checkpoint`, `scenario`, `fill`, and `order`.
3. Add a reading source picker that lists `.qmd` files and headings.
4. Add duplicate, reorder, and delete actions.
5. Add an asset manager for local images.
6. Add a "new module" flow that creates a valid overlay for a discovered module.
7. Add a standalone wrapper later only if non-technical authors need one.
