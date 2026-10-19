PYTHON ?= python3

.PHONY: test demo-suspicious demo-benign demo-markdown docker-build showcase showcase-data help

help:
	@printf '%s\n' \
		'make test              Run the offline test suite' \
		'make demo-suspicious  Compare demo-package 1.0.0 to 2.0.0' \
		'make demo-benign      Compare benign-package 1.0.0 to 1.1.0' \
		'make demo-markdown    Write a pull-request Markdown report' \
		'make showcase         Serve the static demo at http://localhost:4173' \
		'make showcase-data    Regenerate the static demo reports offline' \
		'make docker-build     Build the reproducible Docker image'

test:
	$(PYTHON) -m unittest discover --start-directory tests --verbose
	$(PYTHON) scripts/build_showcase_data.py --check

showcase:
	$(PYTHON) -m http.server 4173 --bind 0.0.0.0 --directory showcase

showcase-data:
	$(PYTHON) scripts/build_showcase_data.py

demo-suspicious:
	$(PYTHON) -m depdiff npm demo-package 1.0.0 2.0.0 --fixtures-dir fixtures

demo-benign:
	$(PYTHON) -m depdiff npm benign-package 1.0.0 1.1.0 --fixtures-dir fixtures

demo-markdown:
	mkdir -p reports
	$(PYTHON) -m depdiff npm demo-package 1.0.0 2.0.0 --fixtures-dir fixtures --format markdown --output reports/demo-review.md

docker-build:
	docker build --tag depdiff:local .
