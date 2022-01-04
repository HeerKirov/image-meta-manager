import json
import yaml
from module.config import load_conf
from module.database import Database


def export(archive: str or None, source: str or None, output: str or None):
    conf = load_conf()
    db = Database(conf["work_path"]["db_path"])

    if archive is None:
        print("\033[1;31m必须指定--archive参数来分割输出。\033[0m")
        exit(1)

    result = db.query_list(folder=archive, source_in=[source] if source is not None else None, status_in=["analysed"])
    mapped_result = {
        "kind": "source",
        "spec": [map_result_item(i) for i in result]
    }

    if output is None:
        print(yaml.safe_dump(mapped_result))
    elif output.endswith(".yaml") or output.endswith(".yml"):
        with open(output, "w") as f:
            yaml.safe_dump(mapped_result, f)
    elif output.endswith(".json"):
        with open(output, "w") as f:
            json.dump(mapped_result, f)
    else:
        print("\033[1;31m不受支持的输出文件类型。\033[0m")
        exit(1)


def map_result_item(item):
    if item["source"] == "complex":
        return {
            "source": "sankaku",
            "sourceId": int(item["pid"]),
            "tags": [{"name": i["name"], "displayName": i["title"], "type": i["type"]} for i in item["tags"]],
            "pools": [i["name"] for i in item["relations"]["pools"]],
            "relations": [int(i) for i in (item["relations"]["parent"] + item["relations"]["children"])]
        }
    else:
        raise Exception("Unsupported source type %s." % (item["source"],))
