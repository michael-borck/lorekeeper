# Pack store policy

Status: first-party and reviewed packs. Public submissions are accepted through
<https://github.com/michael-borck/lorekeeper-packs>.

## Scope

A pack is a small, self-contained course with lessons and optional compiled Ink
stories. It is not a replacement for a full unit, an LMS course, or assessed
material.

## What a pack may contain

- original or properly licensed text, images and Ink stories
- image assets limited to PNG, JPEG, GIF, WebP and AVIF
- exercises whose tests run in the Lorekeeper sandbox
- a complete manifest with id, title, version, author and licence

## What a pack must not contain

- personal data, student work, marks, exam answers or staff-only material
- malware, remote scripts, trackers or network calls from exercise tests
- copied material without permission
- content that is discriminatory, harassing or unsafe for the intended audience

## Safety model

- Every published pack is signed with the Lorekeeper Ed25519 key.
- `lorekeeper verify-store` checks every pack hash and signature before deploy.
- Exercise tests run in a sandboxed iframe with a nonce CSP.
- The sandbox cannot reach the parent page, local storage or the network.
- The learner still chooses to add a pack; nothing installs automatically.

## Review steps

1. Validate the pack with `lorekeeper verify-store` and the pack validator.
2. Read the content for rights, privacy, accuracy and accessibility.
3. Run the exercises in the sandbox and check the failure messages.
4. Sign the pack and publish it through the store build.
5. Record the reviewer, date and pack version.

## Key handling

- The private signing key stays at `~/.lorekeeper/lorekeeper-signing.pem`, mode
  600. It is never committed or pasted into CI logs.
- Public keys live in `player/trusted-keys.js`.
- To rotate:
  1. Generate a new key with a new private path and `--append`.
  2. Rebuild and sign the store with the new key.
  3. Ship the updated `trusted-keys.js` before packs signed with the new key.
  4. Remove the old public key only after every published pack has been
     re-signed.
- If a key is compromised, remove it from the trusted list, re-sign every pack,
  and publish a new app build. Treat the old signatures as invalid.

## Corrections and takedown

A pack can be removed from the catalogue by deleting its entry and pack file,
rebuilding the store and redeploying. Local copies already installed by a
learner are not remotely deleted. Corrections ship as a new pack version.
