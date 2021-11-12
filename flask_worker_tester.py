"""Basic draft of a flask worker tester.
Author: Robert Munnoch

Need to write a tester to throw manyh request at the flask worker to see
how it performs.

On last run:

```
$ python flask_worker_tester.py --requests 10000 --processes 6
 Report: total time 33.247978 total requests 10000 requests per sec: 300.7701701438806
```

"""
import os
from datetime import datetime
from multiprocessing import Pool
from typing import Any, Tuple

import click
import requests


class IFC:
    """Interface Client"""

    host: str
    auth: Tuple[str, str]

    def __init__(self, host, auth):
        self.host = host
        self.auth = auth

    def get(self, url):
        """Simple request."""
        return requests.get(url, auth=self.auth)


ifc = IFC("test", ("a", "p"))


def process(name):
    start = datetime.now()
    result = ifc.get("http://localhost:5000/status/default").json()["status"]
    end = datetime.now()
    tt = (end - start).total_seconds()
    # print(os.getpid(), name, result, tt)
    result["tt"] = tt
    return result


# Run the worker service on a flask
@click.command()
@click.option("--url", default="http://localhost:5000/start")
@click.option("--processes", default=2)
@click.option("--requests", "request_number", default=1000)
def test(url, processes, request_number):
    ifc.get(url)
    start = datetime.now()
    with Pool(processes=processes) as pool:
        result = pool.map(process, range(request_number))
    end = datetime.now()
    tt = (end - start).total_seconds()
    print(
        f" Report: total time {tt} total requests {len(result)} requests per sec: {len(result)/tt}"
    )


if __name__ == "__main__":
    test()
