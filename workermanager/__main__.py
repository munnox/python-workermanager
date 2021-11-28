"""Basic draft of a flask worker.
Author: Robert Munnoch

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
from datetime import datetime
from multiprocessing import Manager
from typing import Tuple

from flask import Flask
from workermanager.processmanager import ProcessManager
from workermanager.context import Context
from workermanager.event import Event
from workermanager.unit import Unit
from workermanager import ResultState
from workermanager.interface import build_simple_app, get_blueprint
import requests
import uuid
import logging

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
logging.basicConfig(
    # format="%(asctime)s %(name) %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.DEBUG,
)

app = Flask("main")

pm = ProcessManager("Main")
worker_api = get_blueprint(pm, onstartunit=startunit)
app.register_blueprint(worker_api)

if __name__ in "__main__":

    app.run(debug=True, threaded=True, processes=1, use_reloader=True)
