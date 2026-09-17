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


def test_to_dict_round_trip() -> None:
    result = run_bayesnmf(MATRIX, {"rank": 2})
    as_dict = result.to_dict()

    assert set(as_dict) == {"signatures", "exposures", "diagnostics"}
    assert as_dict["diagnostics"]["engine"] == "stub"
