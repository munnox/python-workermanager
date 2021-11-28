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
from enum import Enum, auto, Flag
import logging

logger = logging.getLogger(__name__)


class WorkerState(Flag):
    DEFINED = auto()
    RUNNING = auto()


class ResultState(Enum):
    CREATED = auto()
    NOTCREATED = auto()
    STARTED = auto()
    NOTSTARTED = auto()
    STOPPED = auto()
    NOTSTOPPED = auto()
    KILLED = auto()
    NOTKILLED = auto()
    TERMINATED = auto()
    NOTTERMINATED = auto()


# print(__name__)

# if __name__ == "__main__":
#     app = build_simple_app()
#     app.run(debug=True, threaded=True, processes=1, use_reloader=True)
