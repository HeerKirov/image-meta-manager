from .complex import Complex
from .pixiv import Pixiv
from .simulator import Simulator
from module.adapter import Adapter


external_mapping = {
    'complex': Complex
}

available_types = ['complex']


class External(object):
    def __init__(self, strategy, params):
        self.__external = dict()
        self.__strategy = strategy
        self.__params = params

    def get(self, name):
        if name in self.__external:
            return self.__external[name]
        clazz = external_mapping.get(name)
        if clazz is None:
            raise Exception('unsupported external name \'%s\'' % (name,))
        adapter_kwargs = dict()
        external_params = self.__params[name] if name in self.__params else {}
        if 'public' in self.__strategy:
            for k, v in self.__strategy['public'].items():
                adapter_kwargs[k] = v
        if name in self.__strategy:
            for k, v in self.__strategy[name].items():
                adapter_kwargs[k] = v
        adapter = Adapter(**adapter_kwargs)
        obj = clazz(adapter=adapter, params=external_params)
        self.__external[name] = obj
        return obj
