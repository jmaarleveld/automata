import abc
import collections
import enum
import typing

from . import state as _state
from .util import FrozenDict
from automata.match import SimpleMatch


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


_K_TYPE = typing.TypeVar('_K_TYPE')
_ACCEPT_TYPE = typing.Collection[_state.State]
_FUNC_TYPE = typing.Mapping[_K_TYPE, typing.Collection[_state.State]]


class Runner(abc.ABC):

    def __init__(self, start: _state.State,
                 accepting: _ACCEPT_TYPE,
                 transitions: _FUNC_TYPE,
                 multi_valued: bool):
        self.__start = start
        self.__accepting = frozenset(accepting)
        self.__transitions = FrozenDict(transitions)
        self.__multi_value_transitions = multi_valued
        self.__backlog = None
        self.__seen = None
        self.__uid_max = 0

    @classmethod
    def from_optimizer(cls, optimizer):
        pass

    @abc.abstractmethod
    def get_initial_config(self, word):
        pass

    @abc.abstractmethod
    def get_keys(self, configuration):
        pass

    @abc.abstractmethod
    def get_next_config(self, config, key, new_state):
        pass

    @abc.abstractmethod
    def check_accept(self, config) -> RunnerState:
        pass

    @abc.abstractmethod
    def check_accept_sliding(self, config) -> RunnerState:
        """Similar to check_accept, but should not care whether the
        full string is accepted.

        This method is used when finding the longest match in a big
        string and is used for a "running longest". It should not
        care whether the entirety of the string has been matched.
        """

    @abc.abstractmethod
    def make_match(self, word, config) -> SimpleMatch:
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
        self.__setup_run(word)
        while self.__backlog:
            precursor, current = self.__backlog.popleft()
            state = self.check_accept(current)
            if state != RunnerState.CONTINUE:
                if state == RunnerState.ACCEPT:
                    return state
                continue
            self.__advance_states(current, precursor)
        return RunnerState.REJECT

    def find_last(self, string):
        self.__setup_run(string)
        best = None
        while self.__backlog:
            precursor, current = self.__backlog.popleft()
            state = self.check_accept_sliding(current)
            end_check = self.check_accept(current)
            if end_check != RunnerState.CONTINUE:
                if end_check == RunnerState.ACCEPT:
                    best = self.make_match(string, current)
                break
            if state == RunnerState.ACCEPT:
                best = self.make_match(string, current)
            self.__advance_states(current, precursor)
        return best

    def find_first(self, string):
        self.__setup_run(string)
        while self.__backlog:
            precursor, current = self.__backlog.popleft()
            state = self.check_accept_sliding(current)
            end_check = self.check_accept(current)
            if end_check != RunnerState.CONTINUE:
                if end_check == RunnerState.ACCEPT:
                    return self.make_match(string, current)
                break
            if state == RunnerState.ACCEPT:
                return self.make_match(string, current)
            self.__advance_states(current, precursor)

    def find_all(self, string):
        matches = []
        self.__setup_run(string)
        while self.__backlog:
            precursor, current = self.__backlog.popleft()
            state = self.check_accept_sliding(current)
            end_check = self.check_accept(current)
            if end_check != RunnerState.CONTINUE:
                if end_check == RunnerState.ACCEPT:
                    matches.append(self.make_match(string, current))
                break
            if state == RunnerState.ACCEPT:
                matches.append(self.make_match(string, current))
            self.__advance_states(current, precursor)
        return tuple(matches)

    def _search_best(self, string, predicate, finder):
        best = None
        for x in range(len(string)):
            result = finder(string[x:])
            if result is not None:
                result = self.__make_match(result, x, string)
                if best is None:
                    best = result
                else:
                    best = predicate(best, result)
        return best

    def search_longest(self, string):
        return self._search_best(string,
                                 lambda x, y: max(x, y, key=len),
                                 self.find_last)

    def search_shortest(self, string):
        return self._search_best(string,
                                 lambda x, y: min(x, y, key=len),
                                 self.find_last)

    def search_first(self, string):
        for i in range(len(string)):
            result = self.find_first(string[i:])
            if result is not None:
                return self.__make_match(result, i, string)

    def search_last(self, string):
        for i in reversed(range(len(string))):
            result = self.find_last(string[i:])
            if result is not None:
                return self.__make_match(result, i, string)

    def search_all(self, string):
        matches = []
        for i in range(len(string)):
            results = self.find_all(string[i:])
            for result in results:
                matches.append(self.__make_match(result, i, string))
        return matches

    @staticmethod
    def __make_match(match, offset, word):
        return SimpleMatch(start=match.start + offset,
                           stop=match.stop + offset,
                           string=word)

    def __setup_run(self, word):
        self.__backlog = collections.deque()
        self.__seen = collections.defaultdict(set)
        self.__uid_max = 0
        uid = self.__get_next_precursor_id()
        self.__backlog.appendleft((uid, self.get_initial_config(word)))

    def __advance_states(self, current, precursor):
        for key, new_state in self.__next_states(current):
            new = self.get_next_config(current, key, new_state)
            self.__push_to_backlog(new, precursor)

    def __get_next_precursor_id(self):
        self.__uid_max += 1
        return self.__uid_max - 1

    def __push_to_backlog(self, config, precursor):
        if config not in self.__seen[precursor]:
            uid = self.__get_next_precursor_id()
            self.__seen[uid] = self.__seen[precursor] | {config}
            self.__backlog.append((uid, config))

    def __next_states(self, config):
        for key in self.get_keys(config):
            if self.__multi_value_transitions:
                yield from self.__yield_states(key)
            else:
                yield from self.__yield_state(key)

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
