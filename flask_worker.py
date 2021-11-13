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
import os
from datetime import datetime
from multiprocessing import Lock, Manager, Process
from multiprocessing.process import AuthenticationString
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
    event: Event

    def __init__(self, id, event):
        self.id = id
        self.event = event


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

    def get_status_dict(self):
        """Build a status dict for the unit of work."""
        return {"state": self.state, "now": str(datetime.now())}

    def process(self, context):
        for i in range(10):
            self.state = self.state + 1
            self.update()
            print(f"From Unit of Work State: {self.state}")
            # Stay busy for rough seconds
            res = [x ** x for x in range(10_000)]

            if self.state == 10:
                print(self.ifc.get("https://example.com"))

        return context


class ProcessWorker(Process):
    """A process worker to allow to Orchestrate the worker process.
    
    The main contract in this work is that the Unit of work need two methods:

    * process(self, Context) -> Context - Which will run the OnUpdate callback.
    * get_status_dict(self) -> Dict[str, Any] - Builds a dict for the shared
                                                state of of the process to be
                                                made visible.

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

        def update(unit: Unit):
            # print(f"Update status: {unit}")
            print(f"On {os.getpid()}, {id(self)} {unit.get_status_dict()}")
            self.shared_dict.update(unit.get_status_dict())

        self.unit.onUpdate = update

    def run(self):
        """Run the defined unit of work."""
        self.worker_initialisation()

        self.add_update()

        self.unit.process(self.context)

        print(f"Shared dict: {self.shared_dict}")

    # Current workaround to allow a process to be managed
    # Orignally sourced from an answer in:
    # https://stackoverflow.com/questions/29007619/python-typeerror-pickling-an-authenticationstring-object-is-disallowed-for-sec
    def __getstate__(self):
        """called when pickling - this hack allows subprocesses to 
           be spawned without the AuthenticationString raising an error"""
        state = self.__dict__.copy()
        conf = state["_config"]
        if "authkey" in conf:
            # del conf['authkey']
            conf["authkey"] = bytes(conf["authkey"])
        return state

    def __setstate__(self, state):
        """for unpickling"""
        state["_config"]["authkey"] = AuthenticationString(state["_config"]["authkey"])
        self.__dict__.update(state)


class ProcessManager:
    """A Process manager to schedual a worker with a Unit of Work."""

    name: str
    worker: ProcessWorker
    process_state: Any
    manager: Any

    def __init__(self, name):
        self.name = name
        self.manager = Manager()
        # This allow along with the state functions on the Processworker
        # allow them to be pickled but it seem like it does not work in the end
        # The is_alive() does not detect that the process is alive.
        # self.workers = self.manager.dict()

        # Using a local dict for the main dict and can so far run this in one
        # multi threaded single flask process
        self.workers = {}
        # A needed thread and process safe comms object to share shate with the
        # workers and units of work
        self.process_state = self.manager.dict()

    def get_workers(self):
        return {k: {"alive": self.workers[k].is_alive()} for k in list(self.workers.keys())}

    def get_status(self, name):
        """For a summary of the Worker and the unit of work."""
        # print(self.workers)
        if name in self.workers:
            status = {
                "nid": name,
                "manager": self.name,
                "alive": self.workers[name].is_alive(),
                "defined": True,
            }
            status.update(dict(self.process_state[name]))
        else:
            status = {
                "nid": name,
                "manager": self.name,
                "alive": False,
                "defined": False,
            }
        return status

    def define(self, name, context, unit: Unit):
        """Define the process for the worker and the unit of work."""
        # self.process_state = self.manager.dict()
        # self.process_state["event"] = event
        # self.process_state["state"] = 0
        # self.process_state["context"] = context
        # self.process_state["model"] = model
        if name not in self.workers:
            self._create_worker(name, context, unit)
            return True
        else:
            if not self.workers[name].is_alive():
                self._create_worker(name, context, unit)
                return True
            else:
                return False

    def _create_worker(self, name, context, unit):
        self.process_state[name] = self.manager.dict()
        self.workers[name] = ProcessWorker(
            name=self.name,
            context=context,
            unit=unit,
            shared_dict=self.process_state[name],
        )

    def remove(self, name):
        if name in self.workers:
            alive = self.workers[name].is_alive()
            if not alive:
                self.workers[name].close()
                del self.workers[name]
                del self.process_state[name]
                return {"message": f"Worker {name} removed"}
            else:
                return {"message": f"Worker {name} not removed as still running"}
        else:
            return {"message": f"worker {name} not found"}

    def execute(self, name):
        """Start the defined unit of work."""
        self.workers[name].start()


# def run_basic_process(name, pm):
# return pm


# TODO This a flask service build a blueprint
from flask import Blueprint, Flask, g, jsonify

manager = Manager()
# app_context = manager.dict()
pm = ProcessManager("main")


def get_blueprint(pm):
    # global pm
    worker_api = Blueprint("worker_api", __name__, template_folder="templates", static_folder="./")

    @worker_api.route("/")
    def index():
        # TODO Create a simple UI to display debug information
        # return "Worker Server Running"
        return worker_api.send_static_file("index.html")

    @worker_api.route("/start")
    @worker_api.route("/start/<name>")
    def start(name="default"):
        """Start a worker process on a given unit of work."""
        global pm
        ifc = IFC("hosturl", ("admin", "pass"))
        unit = Unit(f"{name} {str(datetime.now())}", ifc)
        # pm = ProcessManager(name, process_state)
        context = Context("test", Event("eventid"))
        if pm.define(name, context, unit):
            pm.execute(name)
        # run_basic_process(name, pm)
        # print(f"PM : {pm} {pm.workers}")
        # app_context[name] = pm.worker
            return jsonify({"message": f"Unit of work {name} create and started."})
        else:
            return jsonify({"message": f"Unit of work {name} not started as one exists."})

    # TODO Add a stop function to request/force a worker and unit of work to stop

    @worker_api.route("/remove")
    @worker_api.route("/remove/<name>")
    def remove(name="default"):
        """Remove A dead worker process."""
        global pm
        return jsonify(pm.remove(name))

    @worker_api.route("/status")
    @worker_api.route("/status/<name>")
    def status(name="default"):
        """Retreive the status of a worker process."""
        global pm
        # print("pm: ", pm.workers)
        status = pm.get_status(name)
        # sleep(0.1)

        # TODO Convert to json object for better M2M access
        return jsonify(
            {"message": f"Return State for {status}", "status": dict(status)}
        )

    @worker_api.route("/workers")
    def workers():
        """Retreive the list of the workers."""
        global pm
        # print("pm: ", pm.workers)
        workers = pm.get_workers()
        # sleep(0.1)

        # TODO Convert to json object for better M2M access
        return jsonify(
            {"message": f"Return worker list for {pm.name}", "workers": workers}
        )

    return worker_api


# Run the worker service on a flask
app = Flask("main")

worker_api = get_blueprint(pm)
app.register_blueprint(worker_api)

# data_dir = "./security/"
# cert = os.path.join(data_dir,"mydomain.crt")
# key = os.path.join(data_dir, "mydomain.key")
# context = None
# context = (cert, key)

if __name__ == "__main__":
    app.run(debug=True, threaded=True, processes=1, use_reloader=True)
