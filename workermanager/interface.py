"""Basic draft of a flask worker flask interface blueprint.
Author: Robert Munnoch

Lots of TODO in this to clean up but it works currently requires further testing.
Seems to work ok and manually testing the server from a browser.

Planning to clean this up and improve a async long running process.

"""
import logging
from flask import Flask, Blueprint, jsonify


logger = logging.getLogger(__name__)


def get_blueprint(pm, onstartunit):
    global gpm
    gpm = pm
    worker_api = Blueprint(
        "worker_api", __name__, template_folder="templates", static_folder="./"
    )

    @worker_api.route("/")
    def index():
        return worker_api.send_static_file("index.html")

    @worker_api.route("/start")
    @worker_api.route("/start/<name>")
    def start(name="default"):
        """Start a worker process on a given unit of work."""
        if callable(onstartunit):
            onstartunit(gpm, name)
        result = gpm.execute(name)
        return jsonify(result)

    @worker_api.route("/kill")
    @worker_api.route("/kill/<name>")
    def kill(name="default"):
        """Kill the process of a worker process."""
        result = gpm.kill(name)
        return jsonify(result)

    @worker_api.route("/terminate")
    @worker_api.route("/terminate/<name>")
    def terminate(name="default"):
        """terminate the process of a worker process."""
        result = gpm.terminate(name)
        return jsonify(result)

    @worker_api.route("/status")
    @worker_api.route("/status/<name>")
    def status(name="default"):
        """Retreive the status of a worker process."""
        status = gpm.get_status(name)
        return jsonify({"message": f"Return State for {name}", "status": dict(status)})

    @worker_api.route("/workers")
    def workers():
        """Retreive the list of the workers."""
        workers = gpm.get_workers()
        return jsonify(
            {"message": f"Return worker list for {gpm.name}", "workers": workers}
        )

    return worker_api


def build_simple_app(pm):
    # Run the worker service on a flask
    app = Flask("main")

    worker_api = get_blueprint(pm)
    app.register_blueprint(worker_api)
    return app
