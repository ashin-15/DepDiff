# Contributor guidance

- Keep the core implementation portable and standard-library-first.
- Never execute fixture or downloaded package code during analysis.
- Keep fixture and report output deterministic so tests and pull requests are
  easy to review.
- Run `make test` after changes to Python code or fixtures.
- Keep user-visible claims narrower than the evidence. A review recommendation
  is not proof of maliciousness or safety.
- Preserve offline operation for tests and demos.
