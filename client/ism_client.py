#!/usr/bin/env python3
# Copyright 2023 iiPython

# Modules
import logging
from time import time, sleep
from socket import gethostname
from argparse import ArgumentParser
from urllib3.exceptions import InsecureRequestWarning

import psutil
import requests

# Initialization
__version__ = "0.1.3"

logging.basicConfig(
    format = "[%(levelname)s] %(message)s",
    level = logging.INFO
)
requests.packages.urllib3.disable_warnings(category = InsecureRequestWarning)

# Conversions
gb_divisor = 1_000_000_000
mb_divisor = 1_048_576

# Data modules
def get_net_usage(interval: int) -> dict:
    stat = psutil.net_io_counters(nowrap = True)
    in_1, out_1 = stat.bytes_recv, stat.bytes_sent
    sleep(interval)
    stat = psutil.net_io_counters(nowrap = True)
    return {
        "in": round((stat.bytes_recv - in_1) / mb_divisor, 3),
        "out": round((stat.bytes_sent - out_1) / mb_divisor, 3)
    }

# Mainloop
def ism_mainloop(args) -> None:
    logging.info(f"ISM Client v{__version__}")
    logging.info(f"Upstream: {args.server} | Token: {args.token}")
    with requests.Session() as session:
        while True:

            # Start logging metrics
            memory_info = psutil.virtual_memory()
            metrics = {
                "data": {
                    "cpu": psutil.cpu_percent(args.interval, percpu = True),
                    "ram": {
                        "total": round(memory_info[0] / gb_divisor, 1),
                        "used": round(memory_info[3] / gb_divisor, 1),
                        "percentage": round((memory_info[3] / memory_info[0]) * 100, 1)
                    },
                    "net": get_net_usage(args.interval),
                    "time": round(time())
                },
                "auth": {
                    "token": args.token,
                    "hostname": args.hostname
                }
            }

            # Send off to remote upstream
            try:
                resp = session.post(
                    f"http{'s' if not args.insecure else ''}://{args.server}/api/upload",
                    json = metrics
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
    parser.add_argument(
        "-i", "--interval",
        default = 5,
        type = int,
        help = "Interval to record CPU/NET data with"
    )
    parser.add_argument(
        "--hostname",
        default = gethostname(),
        help = "The hostname to send to the upstream server"
    )
    parser.add_argument(
        "--insecure",
        help = "Use HTTP instead of HTTPS (unrecommended)",
        action = "store_true"
    )
    ism_mainloop(parser.parse_args())
