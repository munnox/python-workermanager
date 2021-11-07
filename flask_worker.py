from multiprocessing import Process, Lock
from typing import Any, Tuple
from time import sleep
from datetime import datetime
import os
from multiprocessing import Manager

class IFC:
    """Interface Client"""
    host: str
    auth: Tuple[str,str]
    
    def __init__(self, host, auth):
        self.host = host
        self.auth = auth

class Event:
    """Event"""
    id:str
    def __init__(self, id):
        self.id = id

class Context:
    id:str
    ifc: IFC
    state: str = None

    def __init__(self, id, ifc):
        self.id = id
        self.ifc =ifc
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


    def __init__(self, name, ifc):
        self.name = name
        self.ifc = ifc
        self.state = 0
        # self._lock = Lock()
        # self.p = None
    
    def setstate(self, state):
        self.state = state
    
    def process(self, context):
        for i in range(60):
            context.state = context.state + 1
            self.setstate(context.state)
            print(f"State: {context.state}")
            sleep(1)

        return context
    
    
    # def getstate(self):
    #     with self._lock:
    #         print(f"On {os.getpid()}, {id(self)} {id(self.state)} Getting state {self.state}")
    #         local_state = self.state
    #     return local_state

    # def setstate(self, value):
    #     with self._lock:
    #         print(f"On {os.getpid()}, {id(self)} {id(self.state)} Setting state from {self.state} to {id(value)} {value}")
    #         self.state = value

    # def exec(self, e: Event):
    #     context = Context("test", self.ifc)
    #     self.p = Process(target=run, args=(self, context, e))
    #     self.p.start()
    #     # self.run(context)
    #     # self.p.join()

class ProcessWorker(Process):
    def __init__(self, name, api, shared_dict):
        self.name = name
        self.api = api
        self.shared_dict = shared_dict
        super().__init__()

    def run(self):
        context = Context("testid", self.api)
        m = Model(self.name, self.api)
        def setstate(state):
            print(f"set state: {state}")
            self.shared_dict['state'] = state
        m.setstate = setstate
        m.process(context)
        

        print(f"Shared class: {self.shared_dict}")
        # self.c.settest("other test")
        print(f"Shared class: {self.shared_dict}")

class ProcessManager:
    worker: ProcessWorker
    processstate: Any
    state: str
    manager: Any

    def __init__(self):
        self.processstate = None
        self.manager = Manager()

    def getstate(self):
        # with self._lock:
        # print("Getting state", id(self.state), self.state)
        print(f"On {os.getpid()}, {id(self)} {id(self.state)} Getting state from {self.state}")
        local_state = self.state
        return local_state

    def setstate(self, value):
        # with self._lock:
        # print("Setting state", id(self.state), self.state)
        print(f"On {os.getpid()}, {id(self)} {id(self.state)} Setting state from {self.state} to {id(value)} {value}")
        self.state = value

    def exec(self, name, api, m: Model, e: Event):
        context = Context("test", api)
        self.processstate = self.manager.dict()
        self.processstate["state"] = 0
        self.processstate["context"] = context
        self.processstate["model"] = m
        self.worker = ProcessWorker(name=name, api=api, shared_dict=self.processstate)
        self.worker.start()
        # self.process = Process(target=run, args=(model, context, e,d))
        # self.process.start()
        # self.run(context)
        # self.p.join()

def run(localmodel, c, e, d):
    global model
    m = d['model']
    print(f"model: {m}")
    m.state = "started"
    # print("thread", m.name, id(m))
    # m.setstate(1)
    # print("thread", m.getstate())
    # sleep(1)
    # m.setstate(2)
    # print("thread", m.getstate())
    # sleep(1)
    # m.setstate(3)
    # print("thread", m.getstate())

def run_basic_process():
    ifc = IFC("smell", ("admin", "pass"))
    model = Model("base " + str(datetime.now()), ifc)
    pm = ProcessManager()
    pm.exec("processname", ifc, model, Event("eventid"))
    return pm

# print("main", id(model), model)

# for i in range(4):
#     print(f"Main Thread {os.getpid()} query state {pm.processstate['state']}")
#     sleep(2)

# print("query done")

# pm.worker.join()

from flask import Flask, g

app = Flask("main")

@app.route("/")
def index():
    return "Server Running"

@app.route("/start")
def start():
    global pm
    pm = run_basic_process()
    g.pm = pm
    return "Server Running"

@app.route("/status")
def status():
    global pm
    return f"State: {pm.processstate['state']}"

app.run()