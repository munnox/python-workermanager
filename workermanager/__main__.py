"""Basic draft of a flask worker.
Author: Robert Munnoch

to run

# python -m workermanager serve
# python -m workermanager test

Lots of TODO in this to clean up but it works currently requires further testing.
Seems to work ok and manually testing the server from a browser.

Planning to clean this up and improve a async long running process.

Bit of Acsiiflow art https://asciiflow.com/#/

               ┌──────────────────┐
               │  Flask Webserver │
               │ Threaded not Proc│
               │                  │
               │ Run the external │
               │       API        │
               └────────▲─────────┘
                        │
              ┌─────────▼──────────┐
              │ Process Manager    │
              │                    │
              │ Holds common state │
              │ and references to  │
              │ worker managers    │
              └─────────▲──────────┘
                        │
        ┌─────(self.process_status)───────┐
        │               │                 │
  ┌─────▼────┐     ┌────▼─────┐     ┌─────▼────┐
  │ Worker 1 │     │ Worker 2 │     │ Worker 3 │
  │ Process  │     │ Process  │     │ Process  │
  └─────▲────┘     └────▲─────┘     └─────▲────┘
        │               │                 │
┌───────▼──────┐ ┌──────▼───────┐ ┌───────▼──────┐
│              │ │              │ │              │
│ Unit of Work │ │ Unit of Work │ │ Unit of Work │
│              │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘

"""
import itertools
import logging
import os
import uuid
from datetime import datetime
from multiprocessing import Manager, Pool
from typing import Any, Tuple

import click
import requests
from flask import Flask

from workermanager import ResultState
from workermanager.context import Context
from workermanager.event import Event
from workermanager.interface import build_simple_app, get_blueprint
from workermanager.processmanager import ProcessManager
from workermanager.unit import Unit

logger = logging.getLogger(__name__)


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


class Simple(Unit):
    def get_status_dict(self):
        """Build a status dict for the unit of work.
        
        Can and should be over ridder based on the Work to be done.
        """
        return {
            "state": self.state,
            "now": str(datetime.now()),
            "unit_pid": os.getpid(),
        }

    def process(self, context: Context) -> Context:
        """The main process to run for the Unit of Work."""
        count = 0
        for i in range(10):
            count = count + 1
            self.state = str(count)
            # self.update()
            print(f"From Unit of Work State: {self.state}")
            # Stay busy for rough seconds
            res = [x ** x for x in range(10_000)]

        return context


class UOW(Unit):
    def process(self, context: Context) -> Context:
        logger.info("UOW process context: %s", context)
        print("UOW context: ", context)
        self.state = "Run complete"
        return Context


# TODO This a flask service build a blueprint
# from flask import Blueprint, Flask, g, jsonify


# data_dir = "./security/"
# cert = os.path.join(data_dir,"mydomain.crt")
# key = os.path.join(data_dir, "mydomain.key")
# context = None
# context = (cert, key)
# print(__name__)

# if "__main__" in __name__:


def startunit(pm, name):
    unit = Simple("default")
    if name == "default":
        pm.define(name, Context(str(uuid.uuid4()), Event(str(uuid.uuid4()))), unit=unit)
    unit = UOW("test")
    if name == "local":
        pm.define(name, Context(str(uuid.uuid4()), Event(str(uuid.uuid4()))), unit=unit)
    # pm.define("defaulta", {}, unit=unit)


# app = build_simple_app(pm)
def setlogging(level):
    logging.basicConfig(
        # format="%(asctime)s %(name) %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
        level=level,
    )


setlogging(logging.DEBUG)

app = Flask("main")

pm = ProcessManager("Main")
worker_api = get_blueprint(pm, onstartunit=startunit)
app.register_blueprint(worker_api)


@click.command()
def serve():
    """Run the workermanager server.
    
    or use uwsgi

    ```bash
    uwsgi --socket 0.0.0.0:5000 --protocol=http -w workermanager.__main__:app --http-processes 1 --enable-threads
    ```

    or with uwsgi and nginx

    ```bash
    uwsgi -s /tmp/yourapplication.sock --manage-script-name --mount /yourapplication=myapp:app
    ```

    Nginx config

    ```
    location = /yourapplication { rewrite ^ /yourapplication/; }
    location /yourapplication { try_files $uri @yourapplication; }
    location @yourapplication {
      include uwsgi_params;
      uwsgi_pass unix:/tmp/yourapplication.sock;
    }
    ```
    
    """
    setlogging(logging.DEBUG)
    app.run(debug=True, threaded=True, processes=1, use_reloader=True)


ifc = IFC("test", ("a", "p"))


def process(args):
    name, i = args
    start = datetime.now()
    result = ifc.get(f"http://localhost:5000/status/{name}").json()["status"]
    end = datetime.now()
    tt = (end - start).total_seconds()
    # print(os.getpid(), name, result, tt)
    result["client_name"] = name
    result["client_pid"] = os.getpid()
    result["client_tt"] = tt
    return result


# Run the worker service on a flask
@click.command()
@click.option("--url", default="http://localhost:5000")
@click.option("--processes", default=2)
@click.option("--requests", "request_number", default=100)
@click.option("--unit_names", "unit_names", default="default,local")
def test(url, processes, request_number, unit_names):
    """A tester to throw many requests at the worker manager to see
    how it performs.

    On last run:

    ```shell
    $ uwsgi --socket 0.0.0.0:5000 --protocol=http -w workermanager.__main__:app --http-processes 1 --enable-threads &
    $ python -m workermanager test --requests 10000 --processes 6
    Report:
    Total time 43.005247 total requests 20000 requests per sec: 465.05953099164856 avg request: 0.00215026235
    last result: {'alive': False, 'defined': True, 'manager': 'Main', 'manager_pid': 1783492, 'nid': 'local', 'pid': 1783584, 'status': {'now': '2021-11-28 20:30:14.575488', 'state': 'Run complete'}, 'threadid': 140493792761728, 'client_name': 'local', 'client_pid': 1783597, 'client_tt': 0.01106}
    len pid {(1783584, 'local'), (1783575, 'default')}
    len thread {140493792761728}
    len client pid {1783591, 1783593, 1783595, 1783597, 1783599, 1783601}
    ```
    """
    setlogging(logging.INFO)

    unit_names = unit_names.split(",")

    tt, results = start_run(url, processes, request_number, unit_names)

    analysis = analyse_results(processes, unit_names, results)
    click.echo(
        " Report:\n"
        f"Total time {tt} total requests {len(results)} requests per sec: {len(results)/tt} avg request: {tt/len(results)}\n"
        f"last result: {results[-1]}\n"
        f"len pid {set(analysis['server_pids'])}\n"
        f"len thread {set(analysis['server_threadid'])}\n"
        f"len client pid {set(analysis['client_pids'])}\n"
    )


def analyse_results(processes, unit_names, results):
    server_pids = [(r["pid"], r["nid"]) for r in results]
    server_threadid = [r["threadid"] for r in results]
    client_pids = [r["client_pid"] for r in results]
    assert len(set(server_pids)) == len(unit_names)
    assert len(set(client_pids)) == processes
    analysis = {
        "server_pids": server_pids,
        "server_threadid": server_threadid,
        "client_pids": client_pids,
    }
    return analysis


def start_run(url, processes, request_number, unit_names):
    for name in unit_names:
        starturl = os.path.join(url, f"start/{name}")
        click.echo(f"Contacting: {starturl} to start process.")
        resp = ifc.get(starturl)
        click.echo(f"Start response: {resp.json()}")

    start = datetime.now()
    with Pool(processes=processes) as pool:
        results = pool.map(
            process, itertools.product(unit_names, range(request_number))
        )
    end = datetime.now()
    tt = (end - start).total_seconds()

    return tt, results


# grp = click.CommandCollection(sources=[test, serve])

grp = click.Group()
grp.add_command(test, "test")
grp.add_command(serve, "serve")
grp.__doc__ = __doc__

# python -m workermanager serve
# python -m workermanager test
if __name__ in "__main__":
    grp()
