from module.adapter import Adapter
from module.database import Database
from module.external import Complex
from app import config


external_mapping = {
    'complex': Complex
}


def external(name):
    global __external
    if name in __external:
        return __external[name]
    clazz = external_mapping.get(name)
    if clazz is None:
        raise Exception('unsupported external name \'%s\'' % (name,))
    adapter_kwargs = dict()
    if 'public' in config['adapter']:
        for k, v in config['adapter']['public'].items():
            adapter_kwargs[k] = v
    if name in config['adapter']:
        for k, v in config['adapter'][name].items():
            adapter_kwargs[k] = v
    adapter = Adapter(**adapter_kwargs)
    obj = clazz(adapter=adapter)
    __external[name] = obj
    return obj


def database():
    global __database
    if __database is None:
        __database = Database(**config['database'])
    return __database


__external = dict()


__database = None

