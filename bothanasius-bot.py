#!/usr/bin/env python

import asyncio
import uvloop

from botus_receptus import run
from bothanasius import Bothanasius

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


if __name__ == '__main__':
    run(Bothanasius, './config.ini')
