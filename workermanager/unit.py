"""Basic draft of a flask worker unit.
Author: Robert Munnoch

Lots of TODO in this to clean up but it works currently requires further testing.
Seems to work ok and manually testing the server from a browser.

Planning to clean this up and improve a async long running process.

"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Optional

from workermanager.context import Context

logger = logging.getLogger(__name__)


class Unit(ABC):
    """Class to define a Unit of Work Element."""

    name: str
    _state: str
    onUpdate: Optional[Callable[[Any], None]]

    def __init__(self, name):
        self.onUpdate = None
        self.name = name
        self.state = ""

    def run_initialisation(self):
        """The main process to run for the Unit of Work initialisation.
        
        Can and optionally should be overridder based on the Work to be done.
        """
        pass

    def update(self):
        """Call to update the status dict for the manager status."""
        if callable(self.onUpdate):
            self.onUpdate(self)
        else:
            logger.warning("onUpdate callback not callable.")

    def get_status_dict(self):
        """Build a status dict for the unit of work.
        
        Can and should be over ridder based on the Work to be done.
        """
        return {"state": self.state, "now": str(datetime.now())}

    @property
    def state(self) -> str:
        """Get the unit of work state."""
        return self._state

    @state.setter
    def state(self, value: str):
        """Set the unit of work state."""
        self._state = value
        self.update()

    @abstractmethod
    def process(self, context: Context) -> Context:
        """The main process to run for the Unit of Work.
        
        Can and should be over ridder based on the Work to be done.
        """
        return context
