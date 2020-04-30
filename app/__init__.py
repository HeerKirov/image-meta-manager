import yaml


def load_conf(filename):
    with open(filename, 'r') as f:
        return yaml.load(f.read(), Loader=yaml.FullLoader)


config = load_conf('config.yaml')
