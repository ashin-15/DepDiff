# depdiff demonstration guide

All demonstrations run offline from synthetic, harmless fixtures. They do not
execute JavaScript or npm lifecycle scripts.

## Demo A: suspicious upgrade

```console
python3 -m depdiff npm demo-package 1.0.0 2.0.0 --fixtures-dir fixtures
```

The new version adds `postinstall`, filesystem access, and child-process
execution. depdiff reports source locations and returns a `block-recommended`
review recommendation. The process exit code remains zero because analysis
completed successfully; verdicts are not execution failures.

## Demo B: benign upgrade

```console
python3 -m depdiff npm benign-package 1.0.0 1.1.0 --fixtures-dir fixtures
```

The package only changes its implementation in a way that does not match the
default sensitive-capability rules. depdiff reports `ok` and no added
capability evidence.

## Demo C: pull-request Markdown report

```console
mkdir -p reports
python3 -m depdiff npm demo-package 1.0.0 2.0.0 \
  --fixtures-dir fixtures --format markdown --output reports/demo-review.md
```

The resulting `reports/demo-review.md` contains the upgrade summary, capability
table, metadata changes, evidence locations, and assessment reasons.
