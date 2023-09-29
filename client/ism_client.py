# Copyright 2023 iiPython

# Modules
import logging
from time import sleep
from argparse import ArgumentParser

import psutil
from requests import Session

# Initialization
__version__ = "0.1.0"

logging.basicConfig(
    format = "[%(levelname)s] %(message)s",
    level = logging.DEBUG
)

# Conversions
gb_divisor = 1_000_000_000

# Mainloop
def ism_mainloop(args) -> None:
    logging.info(f"ISM Client v{__version__}")
    logging.info(f"Upstream: {args.server} | Token: {args.token}")
    with Session() as session:
        while True:

            # Start logging metrics
            memory_info = psutil.virtual_memory()
            metrics = {
                "cpu": psutil.cpu_percent(5, percpu = True),
                "ram": {
                    "total": round(memory_info[0] / gb_divisor, 1),
                    "used": round(memory_info[3] / gb_divisor, 1),
                    "percentage": round((memory_info[3] / memory_info[0]) * 100, 1)
                }
            }

            # Send off to remote upstream
            try:
                resp = session.post(
                    f"https://{args.server}/upload",
                    json = metrics,
                    verify = False  # Most people won't have a certificate for this
                )
                if resp.status_code != 200:
                    logging.warn(resp.json())

                del resp

            except Exception as e:
                logging.error(e)

            del memory_info, metrics  # Save a few bytes

            # Wait until the next iteration
            sleep(args.delay)

# Handle CLI
if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-s", "--server",
        required = True,
        help = "Upstream server to report stats to"
    )
    parser.add_argument(
        "-t", "--token",
        required = True,
        help = "Access token provided by upstream server"
    )
    parser.add_argument(
        "-d", "--delay",
        default = 10,
        type = int,
        help = "Amount of time between data refreshes"
    )
    ism_mainloop(parser.parse_args())
