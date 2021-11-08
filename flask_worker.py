"""Basic draft of a flask worker.

Lots of TODO in this to clean up but it works currently requires further testing.
Seems to work ok and manually testing the server from a browser.

Planning to clean this up and improve a async long running process.

Author: Robert Munnoch
"""
from multiprocessing import Process, Lock
from typing import Any, Callable, Tuple
from time import sleep
from datetime import datetime
import os
from multiprocessing import Manager


class IFC:
    """Interface Client"""

    host: str
    auth: Tuple[str, str]

    def __init__(self, host, auth):
        self.host = host
        self.auth = auth


class Event:
    """Event"""

    id: str

    def __init__(self, id):
        self.id = id


class Context:
    id: str
    ifc: IFC
    state: str = None

    def __init__(self, id, ifc):
        self.id = id
        self.ifc = ifc
        self.state = 0
        # self._lock = Lock()

    # def getstate(self):
    #     with self._lock:
    #         print("getting state", id(self.state), self.state)
    #         local_state = self.state
    #     return local_state

    # def setstate(self, value):
    #     with self._lock:
    #         print("setting state", id(self.state), self.state)
    #         self.state = value


class Unit:
    """Class to define a Unit of Work Element."""
    name: str
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

        return context


class ProcessWorker(Process):
    """A process worker to allow to Orcestrate the worker process.
    
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
        def update(unit):
            # print(f"Update status: {unit}")
            # print(
            #     f"On {os.getpid()}, {id(self)} {id(self.state)} Getting state from {self.state}"
            # )
            self.shared_dict.update(unit.getstatusdict())

        self.unit.onUpdate = update

    def run(self):
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
        status = {
            "worker": self.name,
            "alive": self.worker.is_alive(),
        }
        status.update(dict(self.process_state))
        return status

    def define(self, context, unit: Unit, event: Event):
        self.process_state = self.manager.dict()
        self.process_state["event"] = event
        # self.process_state["state"] = 0
        # self.process_state["context"] = context
        # self.process_state["model"] = model
        self.worker = ProcessWorker(
            name=self.name, context=context, unit=unit, shared_dict=self.process_state
        )
    
    def execute(self):
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
from flask import Flask, g, Blueprint

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
