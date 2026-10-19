# DepDiff demo video

A **52-second, 1920 x 1080, 30 fps** product demo created with the official
[Remotion skill](https://skills.sh/remotion-dev/skills/remotion-best-practices).
The video uses animated real CLI output and source-evidence callouts, not a
screen recording or an invented application interface. It includes an original
ambient soundtrack and on-screen explanations, with no voiceover.

## Finished artifacts

- `video/out/depdiff-demo.mp4`: H.264 video with stereo AAC audio, about 4.5 MB.
- `video/out/depdiff-poster.png`: opening-scene poster.
- `video/out/checks/`: representative full-resolution scene checks, if generated.

Generated media and `video/public/score.wav` are ignored by Git. The source,
captured CLI evidence, npm lockfile, and soundtrack generator are kept in the
project so the deliverables can be rebuilt.

## Story

- **00:00** - What changed beyond the version number?
- **00:06** - Run the real local fixture comparison.
- **00:15** - Inspect filesystem, installation-script, and process signals.
- **00:25** - Follow exact evidence locations and source snippets.
- **00:36** - Contrast the benign fixture and explain the `ok` limitation.
- **00:43** - Export review evidence as Markdown.
- **00:48** - Try `make demo-suspicious`.

All package examples are synthetic repository fixtures. The capture pipeline
runs DepDiff itself and never executes the fixture JavaScript or lifecycle
scripts. Verdicts are recommendations, not proof of maliciousness or safety.

## Local setup

Use Node.js **22.23.3** (`video/.nvmrc`) and the repository's Python **3.11.2**.
The optional video toolchain is isolated here; it does not change DepDiff's
Python runtime dependencies. All npm dependency versions are exact and locked.

On a clean Debian Bookworm Linux machine, install the browser runtime libraries
and verification tools, or use the container recipe below:

```sh
apt-get update
apt-get install -y --no-install-recommends \
  python3 make ca-certificates ffmpeg fonts-dejavu-core \
  libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 \
  libxdamage1 libxrandr2 libgbm1 libasound2 libcups2 \
  libpango-1.0-0 libcairo2
```

From the repository root:

```sh
npm --prefix video ci
npm --prefix video run browser
npm --prefix video run prepare-demo
npm --prefix video run studio
```

Open <http://localhost:3000/DepDiffDemo> to play, scrub, or edit the composition.
Studio remains a development tool, not a public deployment.

Initial npm installation and Chrome setup need network access. Once the
dependencies and browser are installed, capture, soundtrack synthesis, tests,
preview, and rendering need no external APIs, accounts, or media downloads.
Fonts are bundled npm assets; the soundtrack uses only Python's standard
library. If using another interpreter, the capture script honors `PYTHON`.

## Render and verify

From the repository root:

```sh
npm --prefix video run render
npm --prefix video run poster
npm --prefix video run verify
```

`render` first regenerates evidence and audio, then renders the MP4. `verify`
requires FFmpeg/FFprobe, asserts duration, dimensions, frame rate, frame count,
video/audio codecs, and decodes every audio/video packet to catch corruption.
The fixed inputs and frame-driven animations are deterministic; byte-identical
MP4s across different browsers, platforms, or encoders are not promised.

For representative scene images, run this **inside `video/`**:

```sh
npm exec -- remotion render src/index.ts DepDiffDemo out/checks \
  --frames=330,570,930,1200,1395,1515 --image-format=png --sequence --concurrency=2
```

## Tests

Run the core tests, audio-generator tests, video typecheck, and capture tests
with this command from the repository root:

```sh
make test && npm --prefix video test
```

These checks run offline after npm setup. Capture tests verify byte-identical
JSON regeneration, real CLI parity, both verdicts, exact evidence, Markdown,
working-directory independence, and error handling. The audio tests use a
shortened sample to check deterministic, unclipped stereo PCM without adding
dependencies to the core suite. The MP4 verification is a separate post-render
check, not a substitute for reviewing the visuals.

## Container rebuild

The optional `video/Dockerfile` installs Node, Python, Chrome dependencies,
FFmpeg, local npm dependencies, and the browser. Build with the **repository
root** as the context:

```sh
docker build -f video/Dockerfile -t depdiff-video:local .
mkdir -p video/out
docker run --rm --network none \
  --mount "type=bind,src=$(pwd)/video/out,dst=/app/video/out" \
  depdiff-video:local
```

The image build needs network access. The container's default command renders
the MP4 offline. Docker is not installed in the environment where the initial
video was created, so this recipe has not been container-build verified here.

## Editing and provenance

- `src/Root.tsx`: composition size, frame rate, and 1,560-frame duration.
- `src/Demo.tsx`: seven named scenes, crossfades, soundtrack, and progress line.
- `src/design.tsx`: shared colors, typography, frame, and frame-driven reveals.
- `src/Opening.tsx`, `Compare.tsx`, `Changes.tsx`, `Evidence.tsx`, `Benign.tsx`,
  and `Share.tsx`: the individual scenes.
- `scripts/capture-demo.mjs`: reruns the actual Python CLI into
  `public/demo-data.json`; no timestamps or machine-specific workspace paths.
- `scripts/make-audio.py`: synthesizes the original ambient score.
- `scripts/verify-video.mjs`: validates the rendered deliverable.

The official skill is installed workspace-locally at
`.agents/skills/remotion-best-practices/SKILL.md`, with its supporting references.
`skills-lock.json` records its source and content hash. Its guidance was used
for composition registration, frame-based animation, scene sequencing, local
assets, audio, visual checks, and rendering. Remotion packages are pinned to
**4.0.537**. No global agent configuration was changed.

Inter and IBM Plex Mono are bundled through their pinned Fontsource packages.
No stock footage or externally licensed music is used. Consult the
[Remotion license](https://www.remotion.dev/license) before use in a commercial
workflow that requires a license.
