import time

from module.adapter import Adapter


class Simulator:
    def __init__(self, adapter: Adapter):
        self.__adapter = adapter

    def post(self, _):
        time.sleep(1)
        result = {'tags': [], 'pools': [], 'parent': [], 'children': []}

        return result, 50, 1, None
