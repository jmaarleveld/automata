from automata.fsm import simple_regex_parser


class Regex:

    def __init__(self, pattern):
        self.__fsm = simple_regex_parser.compile_regex(pattern)
        self.__searcher = self.__fsm.runner

    def search(self, haystack):
        return self.__searcher.search_first(haystack)

    def match(self, string):
        return self.__searcher.find_first(string)

    def fullmatch(self, string):
        return self.__searcher.run_with(string)

    def findall(self, text):
        return self.__searcher.find_all(text)

