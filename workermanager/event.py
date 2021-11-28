import logging

logger = logging.getLogger(__name__)


class Event:
    """Event Class for an run instance."""

    id: str

    def __init__(self, id):
        self.id = id

    def __str__(self):
        return f"Event(id='{self.id}')"
