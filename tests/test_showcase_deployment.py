import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "showcase"


class AssetReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = []
        self.references = []
        self.inline_code = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if attributes.get("href", "").startswith("#"):
            self.references.append(attributes["href"][1:])
        for attribute in ("aria-controls", "aria-labelledby", "data-copy-target"):
            self.references.extend(attributes.get(attribute, "").split())
        if tag == "style" or (tag == "script" and not attributes.get("src")):
            self.inline_code.append(tag)
        self.inline_code.extend(
            key for key in attributes if key == "style" or key.startswith("on")
        )
        if tag in {"script", "img", "source"} and attributes.get("src"):
            self.urls.append(attributes["src"])
        if tag == "link" and attributes.get("href"):
            relations = set(attributes.get("rel", "").split())
            if relations & {"stylesheet", "icon", "preload", "modulepreload"}:
                self.urls.append(attributes["href"])


class ShowcaseDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.headers = {
            header["key"].lower(): header["value"]
            for rule in self.config["headers"]
            if rule["source"] == "/(.*)"
            for header in rule["headers"]
        }

    def test_vercel_serves_static_output_without_install_or_build(self):
        self.assertIsNone(self.config["framework"])
        self.assertEqual(self.config["installCommand"], "")
        self.assertEqual(self.config["buildCommand"], "")
        self.assertEqual(self.config["outputDirectory"], "showcase")
        self.assertIs(self.config["cleanUrls"], True)
        self.assertIs(self.config["trailingSlash"], False)
        for override in ("builds", "functions", "routes", "rewrites"):
            with self.subTest(override=override):
                self.assertNotIn(override, self.config)

    def test_csp_allows_self_hosted_assets_and_json_without_inline_code(self):
        directives = {}
        for directive in self.headers["content-security-policy"].split(";"):
            name, *sources = directive.split()
            directives[name] = sources
        for directive in (
            "default-src",
            "script-src",
            "style-src",
            "img-src",
            "font-src",
            "connect-src",
            "base-uri",
        ):
            with self.subTest(directive=directive):
                self.assertEqual(directives[directive], ["'self'"])
        for directive in ("object-src", "frame-ancestors", "form-action"):
            with self.subTest(directive=directive):
                self.assertEqual(directives[directive], ["'none'"])

    def test_security_headers_apply_to_all_paths(self):
        self.assertEqual(self.headers["x-content-type-options"], "nosniff")
        self.assertEqual(self.headers["x-frame-options"], "DENY")
        self.assertEqual(
            self.headers["referrer-policy"], "strict-origin-when-cross-origin"
        )
        self.assertEqual(
            self.headers["permissions-policy"],
            "camera=(), microphone=(), geolocation=()",
        )

    def test_docker_serves_only_static_files_with_pinned_unprivileged_runtime(self):
        dockerfile = (SHOWCASE / "Dockerfile").read_text(encoding="utf-8")
        instructions = {}
        for line in dockerfile.replace("\\\n", " ").splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                name, _, value = line.strip().partition(" ")
                instructions.setdefault(name.upper(), []).append(value.strip())
        self.assertEqual(instructions["FROM"], ["python:3.11.2-slim-bullseye"])
        self.assertEqual(instructions["COPY"], ["showcase/ /srv/showcase/"])
        self.assertEqual(instructions["WORKDIR"], ["/srv/showcase"])
        self.assertEqual(instructions["USER"], ["10001:10001"])
        self.assertEqual(instructions["EXPOSE"], ["4173"])
        self.assertNotIn("ADD", instructions)
        self.assertNotIn("ENTRYPOINT", instructions)
        self.assertEqual(
            instructions["RUN"],
            ["rm -f /srv/showcase/Dockerfile /srv/showcase/.dockerignore"],
        )
        self.assertEqual(
            json.loads(instructions["CMD"][0]),
            [
                "python3",
                "-m",
                "http.server",
                "4173",
                "--bind",
                "0.0.0.0",
                "--directory",
                "/srv/showcase",
            ],
        )
        self.assertTrue((SHOWCASE / ".dockerignore").is_file())

    def test_source_and_referenced_assets_exist(self):
        self.assertTrue((SHOWCASE / "index.html").is_file())
        for name in ("styles.css", "app.js", "data/reports.json"):
            with self.subTest(file=name):
                self.assertTrue((SHOWCASE / name).is_file(), f"Missing source: {name}")

        parser = AssetReferences()
        parser.feed((SHOWCASE / "index.html").read_text(encoding="utf-8"))
        references = [(SHOWCASE, url) for url in parser.urls]
        css = (SHOWCASE / "styles.css").read_text(encoding="utf-8")
        references.extend(
            (SHOWCASE, match.group(2))
            for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css)
        )
        for directory, url in references:
            with self.subTest(url=url):
                parts = urlsplit(url)
                self.assertFalse(parts.scheme, "Showcase assets must be self-hosted")
                self.assertFalse(parts.netloc, "Showcase assets must be self-hosted")
                if not parts.path:
                    continue
                path = unquote(parts.path)
                base = SHOWCASE if path.startswith("/") else directory
                asset = (base / path.lstrip("/")).resolve()
                self.assertTrue(asset.is_relative_to(SHOWCASE.resolve()))
                self.assertTrue(asset.is_file(), f"Missing static asset: {url}")

    def test_internal_links_accessible_references_and_copy_targets_resolve(self):
        parser = AssetReferences()
        parser.feed((SHOWCASE / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(len(parser.ids), len(set(parser.ids)), "Duplicate HTML IDs")
        for reference in parser.references:
            with self.subTest(reference=reference):
                self.assertIn(reference, parser.ids)

    def test_html_does_not_require_inline_scripts_styles_or_event_handlers(self):
        parser = AssetReferences()
        parser.feed((SHOWCASE / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(parser.inline_code, [])


if __name__ == "__main__":
    unittest.main()
