"""Basic draft of a flask worker processworker.
Author: Robert Munnoch

Lots of TODO in this to clean up but it works currently requires further testing.
Seems to work ok and manually testing the server from a browser.

Planning to clean this up and improve a async long running process.

"""
import logging
import os
from multiprocessing import Process
from multiprocessing.process import AuthenticationString
from typing import Any, Dict
from workermanager.context import Context

from workermanager.unit import Unit

logger = logging.getLogger(__name__)


class ProcessWorker(Process):
    """A process worker to allow to Orchestrate the worker process.
    
    The main contract in this work is that the Unit of work need two methods:

    * process(self, Context) -> Context - Which will run the OnUpdate callback.
    * get_status_dict(self) -> Dict[str, Any] - Builds a dict for the shared
                                                state of of the process to be
                                                made visible.

    """

    name: str
    unit: Unit
    context: Context
    shared_dict: Dict[str, Any]

    def __init__(
        self, name: str, unit: Unit, context: Context, shared_dict: Dict[str, Any]
    ):
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
            msg = f"On {os.getpid()}, {id(self)} {unit.get_status_dict()}"
            logger.info(msg)
            self.shared_dict.update({"status": unit.get_status_dict()})

        self.unit.onUpdate = update

    def run(self):
        """Run the defined unit of work."""
        logger.info("Processworker: Start of Run")
        logger.debug("ProcessWorker: Running unit initialisation")
        self.unit.run_initialisation()
        logger.debug("ProcessWorker: Finished unit initialisation")

        logger.debug("ProcessWorker: Adding update callback")
        self.add_update()
        logger.debug("ProcessWorker: Update callback added")

        logger.info("Processworker: Start of Unit Process")
        self.unit.process(self.context)
        logger.info("Processworker: End of Unit Process")

        # TODO Add end run callback to allow an event to be lodged to run at the end of the worker
        logger.info("Processworker: End of Run")

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

