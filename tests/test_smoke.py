from __future__ import annotations


def test_smoke_imports_and_dry_run_pipeline():
    # ensure import
    from main_bot import run

    # should execute without external API calls
    run(dry_run=True)

