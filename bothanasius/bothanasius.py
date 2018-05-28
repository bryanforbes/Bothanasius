from typing import Any
from configparser import ConfigParser
from botus_receptus import db

import logging

log = logging.getLogger(__name__)

extensions = (
    'bothanasius.cogs.mod',
)


class Bothanasius(db.Bot):
    def __init__(self, config: ConfigParser, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)

        for extension in extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                log.exception('Failed to load extension %s.', extension)
