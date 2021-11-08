import multiprocessing.managers as m
from multiprocessing import Manager, Process, Queue
from multiprocessing.managers import BaseManager


class MyManager(BaseManager):
    pass  # Pass is really enough. Nothing needs to be done here.


class WorkerQueue(Process):
    def __init__(self, q):
        self.q = q
        super().__init__()

    def run(self):
        self.q.put("local hello")


class Worker(Process):
    def __init__(self, c):
        self.c = c
        super().__init__()

    def run(self):
        print(f"Shared class: {self.c}, {self.c.gettest()}")
        self.c.settest("other test")
        print(f"Shared class: {self.c}, {self.c.gettest()}")


class WorkerList(Process):
    def __init__(self, m, c):
        self.m = m
        self.c = c
        super().__init__()

    def run(self):
        self.c[0]["newkey"] = "make"
        print(f"Manager: {self.m}, Shared class: {self.c[2]}")
        self.c[3] = -self.c[4]
        # self.c.settest("other test")
        # print(f"Shared class: {self.c}, {self.c.test()}")


class API:
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password


class MySharedClass:
    # stuff...
    def __init__(self, test, api):
        self._test = test
        self.api = api

    def gettest(self):
        return self._test

    def settest(self, value):
        self._test = value


# queue = Queue()
# w = WorkerQueue(queue)
# w.start()

MyManager.register("MySharedClass", MySharedClass, exposed=("gettest", "settest"))

api = API("uri", "u", "p")

print("=== Example 1 ===")
m = MyManager()
m.start()
print(f"Manager address: {m.address}")
c = m.MySharedClass("test", api)
print("main:", c.gettest())
w = Worker(c)
w.start()
w.join()
print("main:", c.gettest())
m.shutdown()

print("=== Example 2 ===")
m = MyManager(address=("0.0.0.0", 50000), authkey=b"abracadabra")
m.start()
print(f"Manager address: {m.address}")
# with MyManager() as m:
c = m.MySharedClass("test", api)
print("main:", c.gettest())
w = Worker(c)
w.start()
w.join()
print("main:", c.gettest())

# s = m.get_server()
# s.serve_forever()

# s = m.get_server()
# s.serve_forever()
m.shutdown()

print("=== Example 3 ===")
m = MyManager(address=("127.0.0.1", 50000), authkey=b"abracadabra")
m.start()
print(f"Manager address: {m.address}")
# with MyManager() as m:
c = m.MySharedClass("test", api)
print("main:", c.gettest())
w = Worker(c)
w.start()
w.join()
print("main:", c.gettest())

# s = m.get_server()
# s.serve_forever()

# s = m.get_server()
# s.serve_forever()
m.shutdown()

print("=== Example 4 ===")
with Manager() as manager:
    # manager.start()
    l = manager.list([i * i for i in range(10)])
    l[0] = manager.dict()
    print("L[0] ", l[0])
    print("L[2] ", l[2])
    w = WorkerList(manager, l)
    w.start()
    w.join()
    print(f"Manager address: {manager.address}")
    print("L[0] ", l[0])
    print("L[3] ", l[3])

print("=== Example 5 ===")
manager = Manager()
# manager.start()

l = manager.list([i * i for i in range(10)])
l[0] = manager.dict()
print("L[0] ", l[0])
print("L[2] ", l[2])
w = WorkerList(manager, l)
w.start()
w.join()
print(f"Manager address: {manager.address}")
print("L[0] ", l[0])
print("L[3] ", l[3])
manager.shutdown()
