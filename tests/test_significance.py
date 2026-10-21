"""Tests for research/significance.py.

The expected Wilson values below are worked out by hand from the formula

    center = (p + z^2 / (2n)) / (1 + z^2 / n)
    half   = z * sqrt(p(1-p)/n + z^2 / (4 n^2)) / (1 + z^2 / n)

with z = 1.96 (z^2 = 3.8416).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import significance  # noqa: E402


def test_wilson_ci_half_success_n50():
    # p = 0.5, n = 50:
    #   1 + z^2/n          = 1.076832
    #   p + z^2/(2n)       = 0.5 + 0.038416 = 0.538416  ->  center = 0.538416 / 1.076832 = 0.5
    # For p = 0.5 the half-width simplifies to z / (2 * sqrt(n + z^2)):
    #   sqrt(50 + 3.8416)  = sqrt(53.8416) = 7.33768
    #   half               = 1.96 / (2 * 7.33768) = 0.133556
    # so the 95% interval is [0.5 - 0.133556, 0.5 + 0.133556] = [36.644%, 63.356%].
    lo, hi = significance.wilson_ci(50, 50)
    assert lo == pytest.approx(36.644, abs=1e-2)
    assert hi == pytest.approx(63.356, abs=1e-2)


def test_wilson_ci_zero_successes_n10():
    # p = 0, n = 10:
    #   1 + z^2/n = 1.38416, z^2/(2n) = 0.19208
    #   center = 0.19208 / 1.38416 = 0.138773
    #   half   = 1.96 * sqrt(3.8416 / 400) / 1.38416 = 0.19208 / 1.38416 = 0.138773
    # The lower bound is therefore 0 and the upper bound is 2 * 0.138773 = 27.755%.
    lo, hi = significance.wilson_ci(0, 10)
    assert lo == pytest.approx(0.0, abs=1e-9)
    assert hi == pytest.approx(27.755, abs=1e-2)


def test_wilson_ci_bounds_and_ordering():
    for pct in (0, 1, 25, 50, 75, 99, 100):
        lo, hi = significance.wilson_ci(pct, 50)
        assert 0.0 <= lo <= pct <= hi <= 100.0


def test_load_results_matches_whole_ids_only(tmp_path):
    state = tmp_path / "state.jsonl"
    lines = [
        {"type": "result", "exp_id": "H2_run", "results": {"0": 50}},
        {"type": "result", "exp_id": "H27_run", "results": {"0": 60}},
        {"type": "result", "hypothesis": "H2", "exp_id": "other", "results": {"0": 70}},
        {"type": "hypothesis", "id": "H2", "prediction": "not a result entry"},
    ]
    state.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    found = significance.load_results(state, "H2")
    assert [e["exp_id"] for e in found] == ["H2_run", "other"]
