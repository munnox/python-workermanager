"""Basic draft of a flask worker context.
Author: Robert Munnoch

Lots of TODO in this to clean up but it works currently requires further testing.
Seems to work ok and manually testing the server from a browser.

Planning to clean this up and improve a async long running process.

"""
import logging

from workermanager.event import Event

logger = logging.getLogger(__name__)


class Context:
    """The Run context of the Units main process."""

    id: str
    event: Event

    def __init__(self, id, event):
        self.id = id
        self.event = event

    def __str__(self):
        return f"Context(id='{self.id}', event={self.event})"
