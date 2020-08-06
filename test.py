from automata.fsm.simple_regex_parser import *

def test(x):
    print('-' * 100)
    print('Regex:', x)
    print_tree(parse_regex(x))


regexes = (
    'abc',
    'a|b',
    'a*',
    '(a)',
    '(ab)*',
    'a|b*',
    'a|(ab)*',
    'a|(ab*)*',
    'a|bc*',
    'a|(bc)d*',
    '(a|b)*'
)

import contextlib
with open('regexes.txt', 'w') as file:
    with contextlib.redirect_stdout(file):
        for r in regexes:
            test(r)

k = compile_regex('a')
assert k.run('a'), k.dump()
assert not k.run('b'), k.dump()
assert not k.run(''), k.dump()
assert not k.run('ab'), k.dump()
assert not k.run('ba'), k.dump()
assert not k.run('aa'), k.dump()

k = compile_regex('ab')
assert not k.run(''), k.dump()
assert not k.run('a'), k.dump()
assert not k.run('b'), k.dump()
assert not k.run('ba'), k.dump()
assert not k.run('aab'), k.dump()
assert k.run('ab'), k.dump()

k = compile_regex('a*')
assert k.run(''), k.dump()
assert k.run('aa'), k.dump()
assert k.run('aaa'), k.dump()
assert not k.run('ab'), k.dump()
assert not k.run('baa'), k.dump()

k = compile_regex('a|b')
assert not k.run(''), k.dump()
assert k.run('a'), k.dump()
assert k.run('b'), k.dump()
assert not k.run('ba'), k.dump()
assert not k.run('ab'), k.dump()
assert not k.run('aa'), k.dump()
assert not k.run('bb'), k.dump()


# Test loop detection

from automata.state import State
from automata.fsm.fsm import NeFSM
s = State()
k = NeFSM(states={s}, alphabet={'a'}, transitions={(s, ''): {s}}, initial=s, accepting={})
assert not k.run('a'), k.dump()


regex = '(a|b)*'
#print_tree(parse_regex(regex))
k = compile_regex(regex)
#k.render()


k = compile_regex('a')
l = k.to_dfsm()
assert NeFSM.from_dfsm(l).to_regex() == 'a', NeFSM.from_dfsm(l).to_regex()

k = compile_regex('abc')
l = k.to_dfsm()
#k.complement().render()
assert NeFSM.from_dfsm(l).to_regex() == 'abc', NeFSM.from_dfsm(l).to_regex()

k = compile_regex('a|b')
l = k.to_dfsm()
assert NeFSM.from_dfsm(l).to_regex() in ('(a)|(b)', '(b)|(a)'), NeFSM.from_dfsm(l).to_regex()


k = compile_regex('(aa)|(ab)')
#print(k.to_regex())
k = NeFSM.from_dfsm(k.to_dfsm())
#print(k.to_regex())


k = compile_regex('a*')
k = NeFSM.from_dfsm(k.to_dfsm())
#print_tree(parse_regex(k.to_regex()))
k = compile_regex(k.to_regex())
#k.render()



#k.render()

#print_tree(parse_regex('a|b*'))
k = compile_regex('a|b*')
#k.render()

k = compile_regex('(abc)*').to_normal_form()
#k.render()


k = compile_regex('(a|b)*')
#k.render()

k = compile_regex('a*')

from automata.pdm.cfg import *


k = (CFGBuilder()
     .add_rules('S', 'AS', 'BS', '')
     .add_rules('A', 'aA', '')
     .add_rules('B', 'bB', '')
     .finalize(start='S'))

l = k.derive('abba')


def print_tree(tree, indent=0):
   from automata.pdm.cfg import Node, Leaf
   if isinstance(tree, Leaf):
       print(' '*indent, tree.symbol)
   else:
       print(' ' * indent, tree.name)
       assert isinstance(tree, Node)
       for child in tree.children:
            print_tree(child, indent+1)


print_tree(l)