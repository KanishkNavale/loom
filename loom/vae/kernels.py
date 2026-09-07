from enum import StrEnum

import torch

SCALES = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]


class Kernel(StrEnum):
    RBF = "rbf"
    IMQ = "imq"


def heuristic_sigma(d: torch.Tensor) -> torch.Tensor:
    mask = ~torch.eye(d.size(0), dtype=torch.bool, device=d.device)
    return d[mask].median().clamp(min=1e-8)


def point_square_distance(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    x_sq = x.pow(2).sum(dim=1, keepdim=True)
    y_sq = y.pow(2).sum(dim=1, keepdim=True)
    dist = torch.addmm(x_sq + y_sq.t(), x, y.t(), alpha=-2.0)
    return dist.clamp_(min=0.0)


def rbf(psq: torch.Tensor, sigma: torch.Tensor) -> torch.Tensor:
    return torch.exp(-psq / (2.0 * sigma))


def imq(psq: torch.Tensor, sigma: torch.Tensor) -> torch.Tensor:
    k = (sigma * psq.new_tensor(SCALES)).view(-1, 1, 1)
    return (k / (k + psq.unsqueeze(0))).mean(0)


def mmd(
    x: torch.Tensor,
    y: torch.Tensor,
    kernel: Kernel = Kernel.IMQ,
    biased: bool = True,
) -> torch.Tensor:
    xy = torch.cat([x, y], dim=0)
    psq = point_square_distance(xy, xy)
    sigma = heuristic_sigma(psq)

    if kernel == Kernel.RBF:
        k = rbf(psq, sigma)

    if kernel == Kernel.IMQ:
        k = imq(psq, sigma)

    N = x.size(0)
    kxx = k[:N, :N]
    kyy = k[N:, N:]
    kxy = k[:N, N:]
    normalizer = 1.0 / (N * (N - 1.0))

    if not biased:
        return (
            (kxx.sum() - kxx.trace()) * normalizer
            + (kyy.sum() - kyy.trace()) * normalizer
            - 2.0 * kxy.mean()
        )

    return kxx.mean() + kyy.mean() - 2.0 * kxy.mean()
