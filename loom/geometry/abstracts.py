import torch
from kornia.geometry import conversions as transform

from loom.abstracts import BaseDataClass
from loom.geometry.validators import is_rotationmatrix


class Pose(BaseDataClass):
    translation: torch.Tensor
    quaternion: torch.Tensor

    @classmethod
    def from_translation_and_so3(
        cls,
        translation: torch.Tensor,
        rotation: torch.Tensor,
    ) -> "Pose":
        if not is_rotationmatrix(rotation):
            raise ValueError(
                "The rotation matrix doesn't suffice the rotational matrix properties"
            )

        quaternion = transform.rotation_matrix_to_quaternion(
            rotation.contiguous(),
        )

        return cls(
            translation=translation,
            quaternion=quaternion,
        )

    @classmethod
    def from_se3(cls, se3: torch.Tensor) -> "Pose":
        translation = se3[:3, 3]
        rotation = se3[:3, :3]

        if not is_rotationmatrix(rotation):
            raise ValueError(
                "The rotation matrix doesn't suffice the rotational matrix properties"
            )

        quaternion = transform.rotation_matrix_to_quaternion(
            rotation.contiguous(),
        )

        return cls(
            translation=translation,
            quaternion=quaternion,
        )

    @property
    def so3(self) -> torch.Tensor:
        so3 = transform.quaternion_to_rotation_matrix(
            self.quaternion,
        )
        return so3.squeeze(dim=0)

    @property
    def se3(self) -> torch.Tensor:
        rotation_translation = torch.hstack(
            (
                self.so3,
                self.translation[:, None],
            )
        )

        padding = torch.as_tensor(
            [0.0, 0.0, 0.0, 1.0],
            dtype=rotation_translation.dtype,
            device=rotation_translation.device,
        )

        return torch.vstack((rotation_translation, padding))
