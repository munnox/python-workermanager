from multiprocessing import Value, Array, Lock
from multiprocessing.context import Process
from typing import ClassVar, Type, TypeVar
import pickle
import base64

_T = TypeVar("_T")


class SharedMemoryManager:
    """A Manager for a shared memory process bridge.
    
    This is mostly to play with shared primitives.

    * value = is a byte array of a set size.
    """

    _state: Array
    _state_size: int
    _state_type: bool
    lock: Lock

    def __init__(self, state_size: int):
        # self.state = state
        self.lock = Lock()
        self._state_size = state_size
        self._state = Array("c", self._state_size, lock=self.lock)

    @property
    def value(self):
        """A shared byte array."""
        return self._state.value

    @value.setter
    def value(self, value: bytes):
        try:
            self._state.value = value
        except ValueError as error:
            raise ValueError(
                f"{error} currently {len(value)} max set at {self._state_size}"
            )

    @property
    def value_unicode(self, encoding="utf-8"):
        """A shared unicode string array with encoding."""
        return self.value.decode(encoding)

    @value_unicode.setter
    def value_unicode(self, value: str, encoding="utf-8"):
        byte_value = bytes(value, encoding=encoding)
        self.value = byte_value


class SharedMemoryProcessManager:
    """A Manager for a shared memory process bridge.
    
    This is mostly to play with shared primitives.

    * value = is a byte array of a set size.
    * complete = is a float to hold a percentage complete.
    """

    _complete: Value

    def __init__(self, state_size: int, complete: float):
        super().__init__(state_size)
        self._complete = Value("d", complete, lock=self.lock)

    @property
    def complete(self):
        """A shared float to hole a percentage comeplete figure."""
        return self._complete.value

    @complete.setter
    def complete(self, value):
        self._complete.value = value


class SharedMemoryObjectManager(SharedMemoryManager):
    """A Manager for a shared memory process bridge.
    
    Subclass to allow object to be pickled across processes.
    """

    @property
    def obj(self):
        """A wrapper to share a generalised class instance."""
        return pickle.loads(base64.b64decode(self.value))

    @obj.setter
    def obj(self, value: Type[_T]):
        self.value = base64.b64encode(pickle.dumps(value))


class RandomTestClass:
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password

    @classmethod
    def f(cls, share: SharedMemoryObjectManager):
        m = share.obj
        m.url = f"https://localhost/{cls.__module__}.{cls.__name__}"
        share.obj = m


def test_shared_manager():
    """A embedded test to show the above object classes working.
    
    run tests with:
    
    ```bash
    pytest sharedmanager.py -vv
    ```
    """

    share = SharedMemoryObjectManager(1000)

    obj = RandomTestClass("http://localhost/", "admin", "pass")
    share.obj = obj
    print(len(share.value_unicode))

    p = Process(target=RandomTestClass.f, args=(share,))
    p.start()
    p.join()

    valid_url = f"https://localhost/{RandomTestClass.__module__}.RandomTestClass"
    print(share.obj.url)
    print(valid_url)
    assert share.obj.url == valid_url


if __name__ == "__main__":
    test_shared_manager()
