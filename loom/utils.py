import torch


def generate_random_rotation_matrix() -> torch.Tensor:
    random_matrix = torch.rand(3, 3)

    centered = random_matrix - torch.mean(random_matrix, dim=-1)
    U, _, VT = torch.linalg.svd(centered)
    V = VT.permute(1, 0)

    # Handling reflection case!
    normalizer = torch.eye(3, dtype=U.dtype, device=V.device)
    normalizer[-1, -1] = torch.linalg.det(V @ U.permute(1, 0))

    return V @ normalizer.detach() @ U.permute(1, 0)
