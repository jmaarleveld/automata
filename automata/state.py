import uuid


class State:

    __used = {None}

    def __init__(self):
        self.__uid = None
        while self.__uid in self.__used:
            self.__uid = uuid.uuid4()

    def __repr__(self):
        return f'{self.__class__.__qualname__}({self.__uid})'

    @property
    def uid(self):
        return self.__uid

    def __eq__(self, other):
        if not isinstance(other, State):
            return False
        return self.uid == other.uid

    def __hash__(self):
        return hash(self.__uid)
