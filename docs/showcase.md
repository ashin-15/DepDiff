# Static showcase

The showcase is plain HTML, CSS, and JavaScript in `showcase/`, with self-hosted
assets and precomputed reports in `showcase/data/reports.json`. It needs no
frontend runtime, dependency installation, API, secrets, or environment variables.
The hosted demo displays saved fixture comparisons; it does not run Python,
analyze uploaded packages, or execute package code in the browser. The Python CLI
remains the way to run an analysis.

## Local preview and report updates

From the repository root, using the project's pinned Python 3.11.2:

```console
make showcase
```

Open <http://localhost:4173>. This runs
`python3 -m http.server 4173 --bind 0.0.0.0 --directory showcase`; stop it with
Ctrl-C. Use HTTP rather than opening `index.html` as a file so the browser can
fetch `./data/reports.json` from the same origin.

The committed reports make previews and deployments independent of a live
analysis service. After changing fixtures, rules, or report generation:

```console
make showcase-data
make test
```

`make showcase-data` runs `python3 scripts/build_showcase_data.py`. `make test`
runs the standard-library test suite, then
`python3 scripts/build_showcase_data.py --check` to reject missing or stale demo
data without rewriting it. Both commands work offline and never execute fixture
code. Include the regenerated JSON with the corresponding source change.

## Deploy to Vercel

1. Import the repository as a Vercel project.
2. Set **Framework Preset** to **Other** and **Root Directory** to `./` (the
   repository root, not `showcase/`).
3. Use the checked-in root `vercel.json`: framework is `null`, the output
   directory is `showcase`, and install and build commands are empty. Clear any
   dashboard overrides that would install dependencies or run a build.
4. No environment variables or secrets are required. Deploy the committed files.

Vercel serves only the `showcase` output directory. There is no Python function,
Node application, or build-time report generation on the host. Regenerate and
check reports locally before deploying when their inputs change.

The configuration enables clean URLs and disables trailing slashes. There is no
catch-all rewrite: a missing JSON or asset URL stays a missing resource. Security
headers apply to all paths. The content security policy permits same-origin
external JavaScript, stylesheets, SVG images, fonts (including local WOFF2), and
the JSON fetch. Keep assets self-hosted and scripts and styles in separate files;
inline code and third-party resource URLs are not permitted by this policy.

After deployment, open the home page and a saved comparison, and confirm
`/data/reports.json` loads. An empty or broken demo should be investigated through
the browser's network and console errors, not by enabling a server-side runtime.

## Static-serving container

Build from the repository root:

```console
docker build -f showcase/Dockerfile -t depdiff-showcase .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  -p 4173:4173 depdiff-showcase
```

Open <http://localhost:4173>. The separate showcase image uses the pinned
`python:3.11.2-slim-bullseye` base and the standard-library HTTP server. It copies
only `showcase/`, removes its Docker deployment files from the served directory,
installs no packages, and runs as unprivileged UID/GID `10001:10001`. The build
needs the base image cached locally or available from the registry. Once built,
serving the bundled demo requires no outbound network access or writable storage.

The root `.dockerignore` controls the repository-root build context for this
command. `showcase/.dockerignore` records showcase-local exclusions; Docker does
not apply it to the root context. The repository's existing CLI Dockerfile has
its own build and run workflow. The local and container HTTP servers are simple
previews; the Vercel response headers come from `vercel.json`.

## Optional real-browser checks

`make test` remains standard-library-only and offline. For UI regression and
automated accessibility checks, use Node.js 22 and the pinned, optional testing
tools below. These tools are not used by the website or installed on Vercel.
Install them inside the ignored project-local `.venv/` directory:

```console
npm install --prefix .venv/showcase-browser --no-save playwright@1.58.2 axe-core@4.11.1
PLAYWRIGHT_BROWSERS_PATH=.venv/showcase-browser/browsers \
  .venv/showcase-browser/node_modules/.bin/playwright install chromium
```

The one-time tool/browser installation needs network access. With `make showcase`
running in another terminal, run the checks (offline after installation):

```console
NODE_PATH="$PWD/.venv/showcase-browser/node_modules" \
  PLAYWRIGHT_BROWSERS_PATH=.venv/showcase-browser/browsers \
  AXE_MODULE=axe-core/axe.min.js node tests/showcase_browser.cjs
```

The runner checks real report contents, finding selection, all output formats,
Markdown download bytes, scenario switching, keyboard controls, copy behavior,
setup commands, FAQ disclosure, mobile navigation, 320/390/768/1440-pixel layouts,
reduced-motion rendering, report-load failure/retry, and no-JavaScript content.
It applies the Vercel security headers to the functional browser session and
rejects third-party requests and browser errors. Axe checks WCAG 2/2.1 A/AA on
desktop and mobile; automated checks are not a complete accessibility audit.
Screenshots and accessibility results go to `reports/showcase-browser/`, which
is ignored by Git. Set `SHOWCASE_URL` to test another local HTTP port.
