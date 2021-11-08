"""Basic draft of a flask worker.

Lots of TODO in this to clean up but it works currently requires further testing.
Seems to work ok and manually testing the server from a browser.

Planning to clean this up and improve a async long running process.

Author: Robert Munnoch
"""
import os
from datetime import datetime
from multiprocessing import Lock, Manager, Process
from time import sleep
from typing import Any, Callable, Tuple

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


class Event:
    """Event Class for an run instance."""

    id: str

    def __init__(self, id):
        self.id = id


class Context:
    """The Run context of the Units main process."""

    id: str
    ifc: IFC

    def __init__(self, id, ifc):
        self.id = id
        self.ifc = ifc


class Unit:
    """Class to define a Unit of Work Element."""

    name: str
    ifc: IFC
    state: str

    onUpdate: Callable[[Any], Any]

    def __init__(self, name, ifc):
        self.name = name
        self.ifc = ifc
        self.state = 0

    def update(self):
        self.onUpdate(self)

    def getstatusdict(self):
        """Build a status dict for the unit of work."""
        return {"state": self.state}

    def process(self, context):
        for i in range(60):
            self.state = self.state + 1
            self.update()
            print(f"From Unit of Work State: {self.state}")
            sleep(1)

            if self.state == 10:
                print(context.ifc.get("https://example.com"))
                print(self.ifc.get("https://example.com"))

        return context


class ProcessWorker(Process):
    """A process worker to allow to Orchestrate the worker process.
    
    The main contract in this work is that the Unit of work need two methods:

    * process(self, Context) -> Context
    * getstatusdict(self) -> Dict[str, Any]

    """

    def __init__(self, name, unit, context, shared_dict):
        self.name = name
        self.unit = unit
        self.context = context
        self.shared_dict = shared_dict
        super().__init__()

    def worker_initialisation(self):
        """Allowing simple one time initialisation."""
        pass

    def add_update(self):
        """Helper to add the shared status update for the model."""

        def update(unit):
            # print(f"Update status: {unit}")
            # print(
            #     f"On {os.getpid()}, {id(self)} {id(self.state)} Getting state from {self.state}"
            # )
            self.shared_dict.update(unit.getstatusdict())

        self.unit.onUpdate = update

    def run(self):
        """Run the defined unit of work."""
        self.worker_initialisation()

        self.add_update()

        self.unit.process(self.context)

        print(f"Shared dict: {self.shared_dict}")


class ProcessManager:
    """A Process manager to schedual a worker with a Unit of Work."""

    worker: ProcessWorker
    process_state: Any
    manager: Any

    def __init__(self, name):
        self.name = name
        self.process_state = None
        self.manager = Manager()

    def getstatus(self):
        """For a summary of the Worker and the unit of work."""
        status = {
            "worker": self.name,
            "alive": self.worker.is_alive(),
        }
        status.update(dict(self.process_state))
        return status

    def define(self, context, unit: Unit, event: Event):
        """Define the process for the worker and the unit of work."""
        self.process_state = self.manager.dict()
        self.process_state["event"] = event
        # self.process_state["state"] = 0
        # self.process_state["context"] = context
        # self.process_state["model"] = model
        self.worker = ProcessWorker(
            name=self.name, context=context, unit=unit, shared_dict=self.process_state
        )

    def execute(self):
        """Start the defined unit of work."""
        self.worker.start()


def run_basic_process(name):
    ifc = IFC("hosturl", ("admin", "pass"))
    unit = Unit(f"{name} {str(datetime.now())}", ifc)
    pm = ProcessManager(name)
    context = Context("test", ifc)
    pm.define(context, unit, Event("eventid"))
    pm.execute()
    return pm


# TODO This a flask service build a blueprint
from flask import Blueprint, Flask, g

app_context = {}

worker_api = Blueprint("worker_api", __name__, template_folder="templates")


@worker_api.route("/")
def index():
    # TODO Create a simple UI to display debug information
    return "Worker Server Running"


@worker_api.route("/start")
@worker_api.route("/start/<name>")
def start(name="default"):
    """Start a worker process on a given unit of work."""
    global app_context
    if name not in app_context:
        app_context[name] = run_basic_process(name)
        return f"Unit of work {name} create and started."
    else:
        return f"Unit of work {name} not started as one exists."


# TODO Add a stop function to request/force a worker and unit of work to stop


@worker_api.route("/remove")
@worker_api.route("/remove/<name>")
def remove(name="default"):
    """Remove A dead worker process."""
    global app_context
    if name in app_context:
        status = app_context[name].getstatus()
        if not status["alive"]:
            app_context[name].worker.close()
            del app_context[name]
            return f"Worker {name} removed"
        else:
            return f"Worker {name} not removed as still running"
    else:
        return f"worker {name} not found"


@worker_api.route("/status")
@worker_api.route("/status/<name>")
def status(name="default"):
    """Retreive the status of a worker process."""
    global app_context
    status = None
    if name in app_context:
        status = app_context[name].getstatus()

    # TODO Convert to json object for better M2M access
    return f"Return State for {status}"


# Run the worker service on a flask

if __name__ == "__main__":
    app = Flask("main")
    app.register_blueprint(worker_api)

    app.run()
