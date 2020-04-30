from module.adapter import Adapter
from module.local import Local
from module.database import Database, STATUS
from external.complex import Complex
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


def local():
    global __local
    if __local is None:
        __local = Local(**config['local'])
    return __local


__external = dict()


__database = None


__local = None
