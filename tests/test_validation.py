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


def test_inverted_rank_range_rejected(client: TestClient) -> None:
    payload = {"matrix": [[1, 2], [3, 4]], "params": {"rank_min": 4, "rank_max": 2}}
    assert client.post("/jobs", json=payload).status_code == 422


def test_rank_range_capped_by_matrix_dimensions(client: TestClient) -> None:
    # Default range is 2..8; a 2x2 matrix cannot support rank_max 8.
    assert client.post("/jobs", json={"matrix": [[1, 2], [3, 4]]}).status_code == 422
    payload = {"matrix": [[1, 2], [3, 4]], "params": {"rank_min": 1, "rank_max": 2}}
    assert client.post("/jobs", json=payload).status_code == 202
