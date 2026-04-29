import torch


class MHA(torch.Module):
    "Scaled Dot-Product Multi-Head Attention"

    def __init__(self, d_model: int, n_heads: int) -> None:
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads

        if not self.head_dim * n_heads == d_model:
            raise ValueError("d_model must be divisible by n_heads")

        self.q_linear = torch.nn.Linear(d_model, d_model)
        self.k_linear = torch.nn.Linear(d_model, d_model)
        self.v_linear = torch.nn.Linear(d_model, d_model)
        self.out_linear = torch.nn.Linear(d_model, d_model)

    @property
    def dim_scaler(self) -> float:
        return self.head_dim**0.5

    def _project(
        self,
        x: torch.Tensor,
        batch_size: int,
        seq_length: int,
    ) -> torch.Tensor:
        return x.view(
            batch_size,
            seq_length,
            self.n_heads,
            self.head_dim,
        ).transpose(1, 2)

    def forward(self, x: torch.Tensor, apply_mask: bool = True) -> torch.Tensor:
        batch_size, seq_length, _ = x.size()
        q = self._project(self.q_linear(x), batch_size, seq_length)
        k = self._project(self.k_linear(x), batch_size, seq_length)
        v = self._project(self.v_linear(x), batch_size, seq_length)

        attn_weights = torch.matmul(q, k.transpose(-2, -1)) / (self.dim_scaler)

        if apply_mask:
            mask = torch.tril(
                torch.ones(
                    seq_length,
                    seq_length,
                    device=x.device,
                )
            )
            attn_weights = attn_weights.masked_fill(mask == 0, float("-inf"))

        attn_logits = torch.softmax(attn_weights, dim=-1)
        attn_output = (
            torch.matmul(attn_logits, v)
            .transpose(1, 2)
            .contiguous()
            .view(batch_size, seq_length, self.d_model)
        )

        return self.out_linear(attn_output)


class GQA(torch.Module):
    "Grouped Query Attention"

    def __init__(self, d_model: int, n_heads: int, n_kv_heads: int) -> None:
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads
        self.head_dim = d_model // n_heads

        if not self.head_dim * n_heads == d_model:
            raise ValueError("d_model must be divisible by n_heads")

        if not n_heads % n_kv_heads == 0:
            raise ValueError("n_heads must be divisible by n_kv_heads")

        self.n_rep = n_heads // n_kv_heads

        self.q_linear = torch.nn.Linear(d_model, d_model)
        self.k_linear = torch.nn.Linear(d_model, n_kv_heads * self.head_dim)
        self.v_linear = torch.nn.Linear(d_model, n_kv_heads * self.head_dim)
        self.out_linear = torch.nn.Linear(d_model, d_model)

    @property
    def dim_scaler(self) -> float:
        return self.head_dim**0.5

    def _project_q(
        self,
        x: torch.Tensor,
        batch_size: int,
        seq_length: int,
    ) -> torch.Tensor:
        return x.view(
            batch_size,
            seq_length,
            self.n_heads,
            self.head_dim,
        ).transpose(1, 2)

    def _project_kv(
        self,
        x: torch.Tensor,
        batch_size: int,
        seq_length: int,
    ) -> torch.Tensor:
        return x.view(
            batch_size,
            seq_length,
            self.n_kv_heads,
            self.head_dim,
        ).transpose(1, 2)

    def _repeat_kv(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, n_kv_heads, seq_length, head_dim = x.shape
        if self.n_rep == 1:
            return x

        return (
            x[:, :, None, :, :]
            .expand(batch_size, n_kv_heads, self.n_rep, seq_length, head_dim)
            .reshape(batch_size, n_kv_heads * self.n_rep, seq_length, head_dim)
        )

    def forward(self, x: torch.Tensor, apply_mask: bool = True) -> torch.Tensor:
        batch_size, seq_length, _ = x.size()
        q = self._project_q(self.q_linear(x), batch_size, seq_length)
        k = self._project_kv(self.k_linear(x), batch_size, seq_length)
        v = self._project_kv(self.v_linear(x), batch_size, seq_length)

        k = self._repeat_kv(k)
        v = self._repeat_kv(v)

        attn_weights = torch.matmul(q, k.transpose(-2, -1)) / (self.dim_scaler)

        if apply_mask:
            mask = torch.tril(
                torch.ones(
                    seq_length,
                    seq_length,
                    device=x.device,
                )
            )
            attn_weights = attn_weights.masked_fill(mask == 0, float("-inf"))

        attn_logits = torch.softmax(attn_weights, dim=-1)
        attn_output = (
            torch.matmul(attn_logits, v)
            .transpose(1, 2)
            .contiguous()
            .view(batch_size, seq_length, self.d_model)
        )

        return self.out_linear(attn_output)
