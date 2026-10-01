from sigserve.sampler import run_bayesnmf

MATRIX = [
    [4, 0, 2],
    [1, 3, 5],
    [0, 6, 1],
    [2, 2, 2],
]


def test_result_shapes() -> None:
    result = run_bayesnmf(MATRIX, {"rank": 2})

    assert len(result.signatures) == 4  # mutation types
    assert all(len(row) == 2 for row in result.signatures)  # rank
    assert len(result.exposures) == 2  # rank
    assert all(len(row) == 3 for row in result.exposures)  # samples


def test_signature_columns_are_distributions() -> None:
    result = run_bayesnmf(MATRIX, {"rank": 2})

    for k in range(2):
        column_sum = sum(row[k] for row in result.signatures)
        assert abs(column_sum - 1.0) < 1e-9


def test_exposures_conserve_sample_totals() -> None:
    result = run_bayesnmf(MATRIX, {"rank": 2})

    for j in range(3):
        sample_total = sum(row[j] for row in MATRIX)
        reconstructed = sum(result.exposures[k][j] for k in range(2))
        assert abs(reconstructed - sample_total) < 1e-9


def test_rank_range_seed_and_trace_in_diagnostics() -> None:
    params = {"rank": None, "rank_min": 2, "rank_max": 4, "seed": 11, "max_iters": 500}
    diagnostics = run_bayesnmf(MATRIX, params).diagnostics

    assert diagnostics["estimated_rank"] == 3
    assert (diagnostics["rank_min"], diagnostics["rank_max"]) == (2, 4)
    assert diagnostics["seed"] == 11
    trace = diagnostics["trace"]
    assert len(trace["iter"]) == len(trace["bic"]) > 0
    assert trace["iter"][-1] <= 500


def test_fixed_rank_wins_over_range() -> None:
    params = {"rank": 2, "rank_min": 2, "rank_max": 8}
    result = run_bayesnmf(MATRIX, params)
    assert result.diagnostics["estimated_rank"] == 2
    assert all(len(row) == 2 for row in result.signatures)


def test_to_dict_round_trip() -> None:
    result = run_bayesnmf(MATRIX, {"rank": 2})
    as_dict = result.to_dict()

    assert set(as_dict) == {"signatures", "exposures", "diagnostics"}
    assert as_dict["diagnostics"]["engine"] == "stub"
