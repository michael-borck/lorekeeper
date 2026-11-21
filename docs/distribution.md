# Distribution and packs

Status: decided 2026-11-06.

## Decision

Lorekeeper ships as a static web app and PWA first. A desktop shell is deferred.

| Option | Use now | Later if needed |
|---|---|---|
| Static web / PWA | Default | Keep |
| Tauri | No | Native pack management, local labs, offline entitlements |
| Electron | No | Same reasons as Tauri, with a larger runtime |

The player is HTML, CSS and JavaScript. SQL runs in WASM, Ink runs in JavaScript,
and the terminal is simulated. There is no native capability that justifies a
desktop build today.

## Why the PWA comes first

- Students can use it in a browser, including lab machines where installs are blocked.
- Install from the browser is optional; the web version keeps working.
- Updates are immediate; there is no signing or notarisation pipeline.
- The same build is the future Tauri or Electron shell if one is ever needed.

The PWA adds a manifest and service worker. It does not add accounts, analytics,
push notifications, permissions or background execution. Progress and packs stay
in IndexedDB unless the learner exports them.

## Hosting

The player is deployed as a static site from `scripts/deploy-site.sh` to the
public `michael-borck/lorekeeper-site` repository. GitHub Pages serves the built
`_site/` output. The course source repositories it compiles from are not
included in this repository.

Custom domain: `lorekeeper.borck.education`, with a Cloudflare `CNAME` for
`lorekeeper` pointing at `michael-borck.github.io`, DNS-only (no proxy) while
GitHub issues the certificate.

## Packs

A pack is inert content, not an app. `python3 -m lorekeeper store` builds the
static catalogue and a sample pack; the player checks the catalogue SHA-256
before storing a pack locally.

```text
pack.json          id, version, title, theme, author, licence, compatibility
courses/           course.json files
content/           overlays
stories/           compiled Ink JSON
assets/            illustrations and media
```

Import copies the pack into local storage or a local library. The app plays from
the local copy and works offline. The catalogue is discovery, not the source of
truth.

## Store model

Start with the SwipeVerse precedent:

- static catalogue on GitHub Pages or Cloudflare Pages
- PR-curated, validated in CI
- app fetches the catalogue and adds a chosen pack to the local library
- no accounts, no backend, no automatic analytics
- free packs ship as static JSON

Paid packs should use Gumroad, Lemon Squeezy or Stripe Payment Links for
checkout and download. Do not build a custom payment backend until volume
justifies it.

## Security

Exercise tests are JavaScript executed in the player page. That is acceptable
for first-party packs and unacceptable for arbitrary third-party packs.

Packs are signed with Ed25519 and exercise tests run in a hidden sandboxed iframe
with a nonce CSP. The sandbox has no parent access, no local storage and no
network. The preview is separate and blocks scripts.

Submissions are reviewed against [`store-policy.md`](store-policy.md), verified
with `lorekeeper verify-store`, and signed before publication. Key rotation and
takedown procedures live in that policy.

## Tauri trigger

Revisit Tauri only if Lorekeeper needs:

- real local terminals or containers for labs;
- pack management outside browser storage;
- offline paid-content entitlements;
- desktop-only integrations.

If that happens, wrap the existing player. Do not fork the lesson format.
