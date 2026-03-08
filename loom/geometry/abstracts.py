import torch
from kornia.geometry import Quaternion
from kornia.geometry.liegroup import Se3, So3

from loom.abstracts import BaseDataClass


class Pose(BaseDataClass):
    translation: torch.Tensor
    quaternion: torch.Tensor

    @property
    def SO3(self) -> So3:
        q = Quaternion(self.quaternion.unsqueeze(dim=0))
        return So3(q)

    @property
    def SE3(self) -> Se3:
        q = Quaternion(self.quaternion.unsqueeze(dim=0))
        t = self.translation.unsqueeze(dim=0)
        return Se3(q, t)
