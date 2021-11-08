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


class Model:
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

    def getstatus(self):
        return {"state": self.state}

    def process(self, context):
        for i in range(60):
            self.state = self.state + 1
            self.update()
            print(f"State: {self.state}")
            sleep(1)

        return context


class ProcessWorker(Process):
    def __init__(self, name, model, context, shared_dict):
        self.name = name
        self.model = model
        self.context = context
        self.shared_dict = shared_dict
        super().__init__()

    def worker_initialisation(self):
        """Allowing simple one time initialisation."""
        pass

    def run(self):
        self.worker_initialisation()

        def update(model):
            print(f"set state: {model}")
            # self.shared_dict["state"] = model.state
            self.shared_dict.update(model.getstatus())

        self.model.onUpdate = update
        self.model.process(self.context)

        print(f"Shared class: {self.shared_dict}")


class ProcessManager:
    worker: ProcessWorker
    process_state: Any
    state: str
    manager: Any

    def __init__(self, name):
        self.name = name
        self.process_state = None
        self.manager = Manager()

    # def getstate(self):
    #     print(
    #         f"On {os.getpid()}, {id(self)} {id(self.state)} Getting state from {self.state}"
    #     )
    #     local_state = self.state
    #     return local_state

    # def setstate(self, value):
    #     print(
    #         f"On {os.getpid()}, {id(self)} {id(self.state)} Setting state from {self.state} to {id(value)} {value}"
    #     )
    #     self.state = value

    def getstatus(self):
        status = {
            "worker": self.name,
            "alive": self.worker.is_alive(),
        }
        status.update(dict(self.process_state))
        return status

    def exec(self, context, model: Model, event: Event):
        self.process_state = self.manager.dict()
        self.process_state["event"] = event
        # self.process_state["state"] = 0
        # self.process_state["context"] = context
        # self.process_state["model"] = model
        self.worker = ProcessWorker(
            name=self.name, context=context, model=model, shared_dict=self.process_state
        )
        self.worker.start()


def run_basic_process(name):
    ifc = IFC("hosturl", ("admin", "pass"))
    model = Model(f"{name} {str(datetime.now())}", ifc)
    pm = ProcessManager(name)
    context = Context("test", ifc)
    pm.exec(context, model, Event("eventid"))
    return pm


# TODO need to add a join for the process maybe
# pm.worker.join()

from flask import Flask, g, Blueprint


app_context = {}

worker_api = Blueprint("worker_api", __name__, template_folder="templates")


@worker_api.route("/")
def index():
    return "Server Running"


@worker_api.route("/start")
@worker_api.route("/start/<name>")
def start(name="default"):
    global app_context
    if name not in app_context:
        app_context[name] = run_basic_process(name)
        return f"Server create and started {name}"
    else:
        return f"Server not started as one exists {name}"


@worker_api.route("/remove")
@worker_api.route("/remove/<name>")
def remove(name="default"):
    global app_context
    if name in app_context:
        status = app_context[name].getstatus()
        if not status["alive"]:
            app_context[name].worker.close()
            del app_context[name]
            return f"worker {name} removed"
        else:
            return f"worker {name} not removed as still running"
    else:
        return f"worker {name} not found"


@worker_api.route("/status")
@worker_api.route("/status/<name>")
def status(name="default"):
    global app_context
    status = None
    if name in app_context:
        status = app_context[name].getstatus()

    return f"State for {status}"


app = Flask("main")
app.register_blueprint(worker_api)

app.run()
