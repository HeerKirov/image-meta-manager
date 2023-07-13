import os
import platform
import yaml


def read_conf(filename):
    try:
        with open(filename, 'r') as f:
            conf = yaml.load(f.read(), Loader=yaml.FullLoader)
            return analyse_conf_env(conf)
    except FileNotFoundError:
        return None


def analyse_conf_env(conf):
    def replace_one(src):
        return src.replace("$HOME", os.environ["HOME"]).replace("$APPDATA", os.path.join(get_appdata_dir(), "imm"))
    if "work_path" in conf:
        work_path = conf["work_path"]
        if "default_work_dir" in work_path and '$' in work_path["default_work_dir"]:
            work_path["default_work_dir"] = replace_one(work_path["default_work_dir"])
        if "archive_dir" in work_path and '$' in work_path["archive_dir"]:
            work_path["archive_dir"] = replace_one(work_path["archive_dir"])
        if "db_path" in work_path and '$' in work_path["db_path"]:
            work_path["db_path"] = replace_one(work_path["db_path"])
    return conf


def get_appdata_dir():
    system = platform.system()
    if system == "Linux":
        return os.path.join(os.environ['HOME'], ".config")
    if system == "Darwin":
        return os.path.join(os.environ['HOME'], "Library/Application Support")
    else:
        return None


def load_conf():
    """
    从合适的位置加载config.yaml配置文件。
    通常，首先尝试从程序的根目录加载。
    如果此文件不存在，那么尝试从用户目录的 %APPDATA%/imm/config.yaml加载。
    再次，尝试从工作目录直接读取。
    :return: 配置文件内容
    """
    conf = read_conf(os.path.join(os.path.split(os.path.realpath(__file__))[0], "../config.yaml"))
    if conf is not None:
        return conf

    appdata_dir = get_appdata_dir()
    conf = appdata_dir and read_conf(os.path.join(appdata_dir, "imm/config.yaml"))
    if conf is not None:
        return conf

    conf = read_conf("config.yaml")
    if conf is not None:
        return conf
    raise FileNotFoundError("Config file cannot be found anywhere.")
