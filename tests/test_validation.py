from fastapi.testclient import TestClient


def submit(client: TestClient, matrix: list, rank: int = 1) -> int:
    payload = {"matrix": matrix, "params": {"rank": rank}}
    return client.post("/jobs", json=payload).status_code


def test_ragged_matrix_rejected(client: TestClient) -> None:
    assert submit(client, [[1, 2], [3]]) == 422


def test_negative_counts_rejected(client: TestClient) -> None:
    assert submit(client, [[1, -2], [3, 4]]) == 422


def test_non_integer_counts_rejected(client: TestClient) -> None:
    assert submit(client, [[1.5, 2], [3, 4]]) == 422


def test_empty_matrix_rejected(client: TestClient) -> None:
    assert submit(client, []) == 422
    assert submit(client, [[]]) == 422


def test_rank_exceeding_matrix_dimensions_rejected(client: TestClient) -> None:
    assert submit(client, [[1, 2], [3, 4]], rank=3) == 422


def test_rank_at_matrix_dimension_accepted(client: TestClient) -> None:
    assert submit(client, [[1, 2], [3, 4]], rank=2) == 202


def test_oversized_matrix_rejected(client: TestClient) -> None:
    too_wide = [[1] * 2001]
    assert submit(client, too_wide) == 422
