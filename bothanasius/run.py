import asyncio
import uvloop

from botus_receptus import cli

from .bothanasius import Bothanasius


def main() -> None:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    runner = cli(Bothanasius, './config.toml')
    runner()
