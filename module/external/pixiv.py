from module.adapter import Adapter

host = 'https://www.pixiv.net'


class Pixiv:
    def __init__(self, adapter: Adapter):
        self.__adapter = adapter

