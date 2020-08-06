class SimpleMatch:

    def __init__(self, start, stop, string):
        self.__start = start
        self.__stop = stop
        self.__string = string

    def __repr__(self):
        args = f'start={self.start}, stop={self.stop}, string={self.match!r}'
        return f'{self.__class__.__name__}({args})'

    def __len__(self):
        return self.__stop - self.__start

    @property
    def start(self):
        return self.__start

    @property
    def stop(self):
        return self.__stop

    @property
    def match(self):
        return self.__string

