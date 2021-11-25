from module.local import scan_rename_files, do_rename_files
from module.config import load_conf


def rename(work_dir, dry_run, verbose):
    """
    整理重命名工作目录下的文件。整理依据配置文件中的几项规则。
    扫描文件仅在工作目录下进行，并且仅扫描supported_extensions中指定的扩展名。如果没有指定此配置，那么会扫描所有文件。
    完成基本扫描之后，根据excludes规则进行排除，符合此规则的项被完全排除出匹配。此规则主要用于排除那些已符合命名规范的文件。
    之后，根据rules规则进行匹配。当filename匹配成功后，根据rename模板生成新的计划名称。而不能匹配的文件也会单独列出，作为需要手动解决问题的提示。
    之后，根据计划名称，在exclude、unmatched、其他rename计划中做重名检测。任何重名冲突都会被从计划列表中摘出，并单独列出作为需要手动解决的提示。

    :param work_dir: 显示指定工作目录，而不是使用默认路径。如果没有配置默认工作目录，则使用当前目录
    :param dry_run: 试运行，生成并打印执行计划，但不实际执行计划
    :param verbose: 打印详细信息。这将打印详细的rename计划。需要注意的是，其它异常计划总是会打印
    """
    conf = load_conf()
    work_dir = work_dir or conf.get("work_path", {})["default_work_dir"]

    result = scan_rename_files(
        work_dir=work_dir,
        rules=conf["rename"]["rules"],
        extensions=conf.get("supported_extensions"),
        excludes=conf["rename"].get("excludes", [])
    )

    print("# 扫描总数: %s, 重命名: %s, 已排除: %s, 未匹配: %s, 重名文件: %s"
          % (result["sum_count"], result["rename_count"], result["excluded_count"], result["unmatched_count"], result["duplicated_count"]))

    if verbose:
        renames = result["renames"]
        if len(renames) > 0:
            print()
            print("# === 重命名项目 %s 项 ===" % (result["rename_count"]),)
            origin_filename_max_length = max([len(o) for (o, _) in renames])
            for e in renames:
                print(("* \033[1;32m%-" + str(origin_filename_max_length) + "s\033[0m -> \033[1;32m%s\033[0m") % e)
        excluded = result["excluded"]
        if len(excluded) > 0:
            print()
            print("# === 已排除项目 %s 项 ===" % (result["excluded_count"]), )
            for item in excluded:
                print("* \033[1;34m%s\033[0m" % (item,))

    unmatched = result["unmatched"]
    if len(unmatched) > 0:
        print()
        print("# === 发现未匹配文件 %s项 ===" % (result["unmatched_count"],))
        for item in unmatched:
            print("* \033[1;31m%s\033[0m" % (item,))

    duplicated = result["duplicated"]
    if len(duplicated) > 0:
        print()
        print("# === 发现重名文件 %s项 ===" % (result["duplicated_count"],))
        for target_filename, filenames in duplicated.items():
            if target_filename in filenames:
                print("* 重命名后与已存在文件\033[1;33m%s\033[0m重名:" % (target_filename,))
                for f in filenames:
                    if f != target_filename:
                        print("  * \033[1;33m%s\033[0m" % (f,))
            else:
                print("- 重命名为相同文件名\033[1;33m%s\033[0m:" % (target_filename,))
                for f in filenames:
                    print("  * \033[1;33m%s\033[0m" % (f,))

    print()

    if not dry_run and len(result["renames"]) > 0:
        do_rename_files(work_dir, result["renames"])
        print("\033[1;32m# 已重命名%s个文件。\033[0m" % (result["rename_count"]))

    if len(unmatched) > 0 or len(duplicated) > 0:
        print("\033[1;33m# 存在无法处理的未匹配或重名文件。请手动完成处理。\033[0m")
