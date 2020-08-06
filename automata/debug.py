import abc
import string
import random


from graphviz import Digraph


class Formatter(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    def get_source_uid(key):
        pass

    @staticmethod
    @abc.abstractmethod
    def get_target_uid(value):
        pass

    @staticmethod
    @abc.abstractmethod
    def get_label(key, value):
        pass


def render(states, transitions, start, accepting, formatter):
    dot = Digraph()
    dot.attr('node', shape='circle')

    names = {}

    def name(x):
        if x not in names:
            y = random.choice(string.ascii_uppercase)
            while y in names.values():
                y += random.choice(string.ascii_uppercase)
            names[x] = y
        return names[x]

    for state in states:
        if state == start and state in accepting:
            dot.attr('node', shape='tripleoctagon')
        elif state in accepting:
            dot.attr('node', shape='doublecircle')
        elif state == start:
            dot.attr('node', shape='octagon')
        dot.node(str(state.uid), name(state.uid))
        dot.attr('node', shape='circle')

    for key, values in transitions.items():
        for value in values:
            dot.edge(formatter.get_source_uid(key),
                     formatter.get_target_uid(value),
                     label=formatter.get_label(key, value))

    print(dot.source)
    dot.render('fsm.gv', view=True)