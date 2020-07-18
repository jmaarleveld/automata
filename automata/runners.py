import abc
import collections
import enum

from .util import FrozenDict


class RunnerState(enum.Enum):
    CONTINUE = enum.auto()
    ACCEPT = enum.auto()
    REJECT = enum.auto()

    @classmethod
    def from_bool(cls, flag):
        if flag:
            return cls.ACCEPT
        return cls.REJECT

    def __bool__(self):
        if self == self.ACCEPT:
            return True
        elif self == self.REJECT:
            return False
        raise ValueError(self)


class Runner(abc.ABC):

    def __init__(self, start, accepting, transitions, multi_valued):
        self.__start = start
        self.__accepting = frozenset(accepting)
        self.__transitions = FrozenDict(transitions)
        self.__multi_value_transitions = multi_valued
        self.__backlog = None
        self.__seen = None
        self.__uid_max = 0

    @abc.abstractmethod
    def get_initial_config(self, word):
        pass

    @abc.abstractmethod
    def get_key(self, configuration):
        pass

    @abc.abstractmethod
    def get_nondeterministic_key(self, configuration):
        pass

    @abc.abstractmethod
    def get_next_config(self, config, key, new_state):
        pass

    @abc.abstractmethod
    def check_accept(self, config) -> RunnerState:
        pass

    @property
    def initial_state(self):
        return self.__start

    @property
    def accepting_states(self):
        return self.__accepting

    @property
    def transitions(self):
        return self.__transitions

    def run_with(self, word):
        self.__backlog = collections.deque()
        self.__seen = collections.defaultdict(set)
        self.__uid_max = 0
        uid = self.__get_next_precursor_id()
        self.__backlog.appendleft((uid, self.get_initial_config(word)))
        while self.__backlog:
            precursor, current = self.__backlog.popleft()
            state = self.check_accept(current)
            if state != RunnerState.CONTINUE:
                if state == RunnerState.ACCEPT:
                    return state
                continue
            for key, new_state in self.__next_states(current):
                new = self.get_next_config(current, key, new_state)
                self.__push_to_backlog(new, precursor)
        return RunnerState.REJECT

    def __get_next_precursor_id(self):
        self.__uid_max += 1
        return self.__uid_max - 1

    def __push_to_backlog(self, config, precursor):
        if config not in self.__seen[precursor]:
            uid = self.__get_next_precursor_id()
            self.__seen[uid] = self.__seen[precursor] | {config}
            self.__backlog.append((uid, config))

    def __next_states(self, config):
        key = self.get_key(config)
        if self.__multi_value_transitions:
            yield from self.__yield_states(key)
        else:
            yield from self.__yield_state(key)
        key = self.get_nondeterministic_key(config)
        if key is not None:
            yield from self.__yield_states(key)

    def __yield_states(self, key):
        try:
            for state in self.__transitions[key]:
                yield key, state
        except KeyError:
            pass

    def __yield_state(self, key):
        try:
            yield key, self.__transitions[key]
        except KeyError:
            pass
