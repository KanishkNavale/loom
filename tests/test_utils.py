import torch

from loom.utils import generate_random_rotation_matrix


def test_generate_random_rotation_matrix_shape():
    """Test that the generated matrix has the correct shape."""
    matrix = generate_random_rotation_matrix()
    assert matrix.shape == (3, 3)


def test_generate_random_rotation_matrix_orthogonal():
    """Test that the generated matrix is orthogonal (R @ R.T = I)."""
    matrix = generate_random_rotation_matrix()
    result = matrix @ matrix.T
    identity = torch.eye(3, dtype=matrix.dtype, device=matrix.device)
    assert torch.allclose(result, identity, atol=1e-6)


def test_generate_random_rotation_matrix_determinant():
    """Test that the determinant is 1 (proper rotation, not reflection)."""
    matrix = generate_random_rotation_matrix()
    det = torch.linalg.det(matrix)
    assert torch.allclose(det, torch.tensor(1.0), atol=1e-6)


def test_generate_random_rotation_matrix_randomness():
    """Test that different calls produce different matrices."""
    matrix1 = generate_random_rotation_matrix()
    matrix2 = generate_random_rotation_matrix()
    assert not torch.allclose(matrix1, matrix2, atol=1e-6)


def test_generate_random_rotation_matrix_preserves_norm():
    """Test that rotation preserves vector norms."""
    matrix = generate_random_rotation_matrix()
    vector = torch.tensor([1.0, 2.0, 3.0])
    rotated = matrix @ vector

    original_norm = torch.linalg.norm(vector)
    rotated_norm = torch.linalg.norm(rotated)

    assert torch.allclose(original_norm, rotated_norm, atol=1e-6)
