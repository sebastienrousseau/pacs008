"""Performance baselines for pacs008.

Suites in this directory are marked with ``@pytest.mark.perf`` and are
**not** collected by the default ``pytest`` run. Invoke explicitly with::

    poetry run pytest tests/perf/ -m perf --benchmark-only --no-cov

Numbers are recorded in ``BENCHMARKS.md`` at the repo root.
"""
