"""Basic draft of a flask worker processmanager.
Author: Robert Munnoch

Lots of TODO in this to clean up but it works currently requires further testing.
Seems to work ok and manually testing the server from a browser.

Planning to clean this up and improve a async long running process.

"""

import logging
import os
import threading
from multiprocessing import Manager
from typing import Any, Dict

from workermanager import ResultState
from workermanager.context import Context
from workermanager.processworker import ProcessWorker
from workermanager.unit import Unit

logger = logging.getLogger(__name__)


class ProcessInfo:
    def __init__(self, process, state):
        self.process = process
        self.state = state


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
        return {
            k: {"defined": self.isdefined(k), "alive": self.isrunning(k)}
            for k in list(self.workers.keys())
        }

    def get_status(self, name):
        """For a summary of the Worker and the unit of work."""
        # print(self.workers)
        status = {
            "nid": name,
            "manager": self.name,
            "manager_pid": os.getpid(),
            "threadid": threading.get_ident(),
            "alive": False,
            "defined": False,
        }
        if name in self.workers:
            status.update(
                {
                    "alive": self.workers[name].process.is_alive(),
                    "defined": True,
                    "status": self.workers[name].state,
                    "pid": self.workers[name].process.pid,
                }
            )
            status.update(dict(self.process_state[name]))
        logger.debug("Get Status: %s", status)
        return status

    def isdefined(self, name):
        return name in self.workers

    def isrunning(self, name):
        return self.isdefined(name) and self.workers[name].process.is_alive()

    def define(self, name: str, context: Context, unit: Unit):
        """Define the process for the worker and the unit of work."""
        result = {
            "pid": os.getpid(),
            "state": ResultState.CREATED.name,
            "message": f"Unit of work {name} create and started.",
        }
        if not self.isdefined(name):
            self._create_worker(name, context, unit)
        else:
            if not self.isrunning(name):
                self.workers[name].process.close()
                self._create_worker(name, context, unit)
            else:
                result.update(
                    {
                        "state": ResultState.NOTCREATED.name,
                        "message": f"Unit of work {name} not started as one exists.",
                    }
                )
        logger.debug("Defined: %s", result)
        return result

    def _create_worker(self, name: str, context: Context, unit: Context):
        self.process_state[name] = self.manager.dict()
        self.workers[name] = ProcessInfo(
            ProcessWorker(
                name=self.name,
                context=context,
                unit=unit,
                shared_dict=self.process_state[name],
            ),
            ResultState.CREATED.name,
        )

    # def remove(self, name: str) -> Dict[str, Any]:
    #     result = {"pid": os.getpid()}
    #     if self.isdefined(name) and not self.isrunning(name):
    #         # alive = self.workers[name].is_alive()
    #         # if not alive:
    #         self.workers[name].close()
    #         del self.workers[name]
    #         del self.process_state[name]
    #         result.update({"state": "removed", "message": f"Worker {name} removed"})
    #     else:
    #         result.update(
    #             {
    #                 "state": "stillrunning",
    #                 "message": f"Worker {name} not removed as still running",
    #             }
    #         )
    #     # else:
    #     #     result.update({"state": "notfound", "message": f"worker {name} not found"})
    #     return result

    def execute(self, name):
        """Start the defined unit of work."""
        result = {
            "pid": os.getpid(),
            "state": ResultState.NOTSTARTED.name,
            "message": f"Unit of work {name} cannot be started.",
        }
        if self.isdefined(name) and not self.isrunning(name):
            self.workers[name].process.start()
            self.workers[name].state = ResultState.STARTED.name
            result.update(
                {
                    "state": ResultState.STARTED.name,
                    "message": f"Unit of work {name} create and started.",
                }
            )
        logger.debug("Execute: %s", result)
        return result

    def kill(self, name):
        """Kill the defined unit of work."""
        result = {
            "pid": os.getpid(),
            "state": ResultState.NOTSTOPPED.name,
            "message": f"Unit of work {name} cannot be stopped (killed).",
        }
        if self.isdefined(name) and self.isrunning(name):
            self.workers[name].process.kill()
            self.workers[name].state = ResultState.KILLED.name
            result.update(
                {
                    "state": ResultState.STOPPED.name,
                    "message": f"Unit of work {name} stopped (killed).",
                }
            )
        logger.debug("Kill: %s", result)
        return result

    def terminate(self, name):
        """Forciably terminate the defined unit of work."""
        result = {
            "pid": os.getpid(),
            "state": ResultState.NOTTERMINATED.name,
            "message": f"Unit of work {name} cannot be stopped (terminate).",
        }
        if self.isdefined(name) and self.isrunning(name):
            self.workers[name].process.terminate()
            self.workers[name].process.join()
            self.workers[name].state = ResultState.TERMINATED.name
            result.update(
                {
                    "state": ResultState.TERMINATED.name,
                    "message": f"Unit of work {name} stopped (terminate).",
                }
            )
        logger.debug("Terminate: %s", result)
        return result
