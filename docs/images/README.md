# README images

These PNGs show the repository's own static showcase, self-hosted fonts, and
precomputed synthetic fixture reports. They are documentation assets, not
screenshots of live package analysis or evidence of maliciousness or safety.
The project logo is reused directly from `showcase/assets/favicon.svg`.

| Image | Content |
| --- | --- |
| `suspicious-upgrade.png` | Added install-script, process, and filesystem signals, with source evidence. |
| `benign-upgrade.png` | No new capability signal under the default policy, including the safety caveat. |
| `capability-explorer.png` | Seven capability categories and an illustrative child-process pattern. |

## Regenerate

Use the pinned optional browser tools from [the showcase guide](../showcase.md#optional-real-browser-checks).
With `make showcase` running, execute this from the repository root:

```sh
NODE_PATH="$PWD/.venv/showcase-browser/node_modules" \
  PLAYWRIGHT_BROWSERS_PATH=.venv/showcase-browser/browsers \
  node scripts/capture_readme_images.cjs
```

Capture uses a fixed 1440 x 1050 viewport, 1x device scale, dark mode, loaded
local fonts, disabled animations, and explicit scenario selection. Once the
optional browser tooling is installed, capture works offline and blocks
third-party requests. It never executes fixture code. Include the PNGs with
README changes so relative image links work on GitHub and in clean checkouts.
