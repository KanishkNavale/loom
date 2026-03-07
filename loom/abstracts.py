from pathlib import Path
from typing import Any, Dict, Type, TypeVar

from omegaconf import DictConfig, ListConfig, OmegaConf
from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound="BaseDataClass")


class BaseDataClass(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        arbitrary_types_allowed=True,
        ignored_types=(type(lambda: None),),
    )

    @property
    def as_dictionary(self) -> dict:
        return self.model_dump(exclude_none=True)

    @property
    def as_json(self) -> str:
        return self.model_dump_json(exclude_none=True) + "\n"

    @classmethod
    def from_dictionary(
        cls: Type[T],
        dictionary: Dict | DictConfig | ListConfig,
    ) -> T:
        return cls(**dictionary)  # type: ignore

    @classmethod
    def from_yaml(cls: Type[T], path: str) -> T:
        config_path = Path(path).resolve()

        if not config_path.exists():
            raise FileNotFoundError(
                f"Could not find the specified config. file at: {config_path}"
            )

        return cls.from_dictionary(OmegaConf.load(config_path))

    @classmethod
    def from_json(cls: Type[T], path: str) -> T:
        config_path = Path(path).resolve()

        if not config_path.exists():
            raise FileNotFoundError(
                f"Could not find the specified config. file at: {config_path}"
            )

        return cls.from_dictionary(OmegaConf.load(config_path))

    def __post_init__(self) -> None:
        pass

    def model_post_init(self, __context: Any) -> None:
        return self.__post_init__()
