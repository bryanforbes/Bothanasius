# flake8: noqa
from .engine import GinoEngine
from sqlalchemy.engine.strategies import EngineStrategy
from typing import Any, Optional, ClassVar

class GinoStrategy(EngineStrategy):
    name: ClassVar[str] = ...
    engine_cls = GinoEngine
    def create(self, name_or_url: Any, loop: Optional[Any] = ..., *args: Any, **kwargs: Any): ...  # type: ignore
