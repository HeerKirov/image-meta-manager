import os
import re
import datetime


def get_today_archive(offset: int or None, split: int or None):
    now = datetime.datetime.now()
    if offset is not None:
        now = now - datetime.timedelta(hours=offset)
    return "%s.%s" % (now.strftime("%Y-%m-%d"), split) if split is not None else now.strftime("%Y-%m-%d")


def __get_fullname(name: str, extension: str or None):
    return "%s.%s" % (name, extension) if extension is not None else name


def __filter_into(li: list, condition):
    """
    根据condition,将li拆分进两个列表。
    """
    a, b = [], []
    for item in li:
        if condition(item):
            a.append(item)
        else:
            b.append(item)
    return a, b


def __get_name_and_extension(filename: str):
    """
    取得指定文件的名称和扩展名部分。
    """
    p = filename.rfind('.')
    return (filename[:p], filename[p + 1:]) if p >= 0 else (filename, None)


def __get_files_in_directory(directory: str):
    """
    扫描指定目录下的所有文件。
    :param directory: 目录位置
    :return: list[str] filenames
    """
    result = []
    for top, dirs, non_dirs in os.walk(directory):
        result.extend(non_dirs)
    return result


def __split_and_filter_extensions(filenames: list[str], extensions: list[str]):
    result = []
    for filename in filenames:
        n, e = __get_name_and_extension(filename)
        if extensions is None or e in extensions:
            result.append((n, e))
    return result


def __next_pattern(template, begin=0):
    start = template.find('{', begin)
    end = template.find('}', begin)
    return (start, end, template[start + 1:end]) if 0 <= start < end else (-1, -1, None)


def __replace_template(template: str, take):
    """
    将template中的占位符替换掉。
    :param template: 携带{}占位符的文本
    :param take: lambda表达式。根据参数决定替换内容。参数可能是索引int，也可能是命名组str
    :return: str
    """
    begin = 0
    while True:
        start, end, pattern = __next_pattern(template, begin)
        if pattern is None:
            return template
        elif pattern.isdigit():
            value = take(int(pattern))
        else:
            value = take(pattern)
        template = template[:start] + value + template[end + 1:]
        begin = start + len(value)


def __get_rename(name: str, rules: list[dict]):
    """
    根据规则，匹配得到重命名后的名称。如果没有匹配，返回None。
    """
    for rule in rules:
        matcher = rule["filename"].match(name)
        if matcher is not None:
            return __replace_template(rule["rename"], lambda k: matcher.group(k))
    return None


def __split_duplicated_names(renamed_files: list[(str, str, str)], other_files: set[str]):
    """
    搜索并分离出重名的文件。
    :param renamed_files: rename列表
    :param other_files: 其他文件列表，来自excluded/unmatched，与它们重名也算做重名文件。
    :return list[(str, str, str)], dict[str, list[str]] 给出无重名文件列表，和重名文件集，结构为{最终文件: 现有文件名列表}
    """
    # 重名字典，key是最终filename，value则是renamed list清单
    name_map: dict[str, (list[str], str, str)] = dict()
    for (name, extension, rename) in renamed_files:
        re_filename = __get_fullname(rename, extension)
        if re_filename in name_map:
            (names, _, _) = name_map[re_filename]
        else:
            names = list()
            name_map[re_filename] = (names, extension, rename)
        names.append(name)

    # 从字典中找出与other_files名称相符，或names数量超过1的项，作为重名文件集。剩下的则放入无重名文件列表
    duplicated = dict()
    not_duplicated = []
    for (filename, (names, extension, rename)) in name_map.items():
        if filename in other_files:
            duplicated[filename] = [*[__get_fullname(name, extension) for name in names], filename]
        elif len(names) > 1:
            duplicated[filename] = [__get_fullname(name, extension) for name in names]
        else:
            not_duplicated.append((names[0], extension, rename))

    return not_duplicated, duplicated


def scan_rename_files(work_dir: str, rules: list[dict], extensions: list[str], excludes: list[str]):
    """
    扫描指定的工作目录，然后识别符合重命名规则的文件列表。
    :param work_dir: 工作目录
    :param rules: 重命名规则。结构参考config.yaml的rename.rules
    :param excludes: 排除规则。包含所有排除的正则表达式。它应该包含包括重命名后的文件名的匹配模式
    :param extensions: 支持扫描的文件类型
    """
    # 预处理规则
    rules = [{"filename": re.compile(rule["filename"]), "rename": rule["rename"]} for rule in rules]
    excludes = [re.compile(s) for s in excludes]
    # 扫描并过滤基本文件列表
    files: list[(str, str)] = __split_and_filter_extensions(__get_files_in_directory(work_dir), extensions)
    # 过滤掉exclude列表
    included_files, excluded_files = __filter_into(files, lambda f: len([1 for e in excludes if e.match(f[0])]) <= 0)
    excluded: list[str] = [__get_fullname(name, extension) for (name, extension) in excluded_files]
    # 根据文件列表生成重命名清单，然后过滤出unmatched列表和matched列表
    renamed_files: list[(str, str, str or None)] = [(name, extension, __get_rename(name, rules)) for (name, extension) in included_files]
    matched_files, unmatched_files = __filter_into(renamed_files, lambda t: t[2] is not None)
    unmatched: list[str] = [__get_fullname(name, extension) for (name, extension, _) in unmatched_files]
    # 根据清单，将matched中的重名项过滤出来
    not_duplicated, duplicated = __split_duplicated_names(matched_files, set(unmatched).union(set(excluded)))
    # 生成重命名计划列表
    renames = [(__get_fullname(name, extension), __get_fullname(rename, extension)) for (name, extension, rename) in not_duplicated]
    # 生成执行计划/执行报告
    return {
        "sum_count": len(files),         # 已扫描的文件总数。指符合扩展名列表的所有文件。它等于下面所有文件数之和
        "rename_count": len(renames),
        "excluded_count": len(excluded),
        "unmatched_count": len(unmatched),
        "duplicated_count": len(files) - len(renames) - len(excluded) - len(unmatched),
        "renames": renames,
        "excluded": excluded,
        "unmatched": unmatched,
        "duplicated": duplicated
    }


def do_rename_files(work_dir, rename_list: list[(str, str)]):
    """
    执行重命名计划。
    """
    for (old, new) in rename_list:
        os.rename(os.path.join(work_dir, old), os.path.join(work_dir, new))


def __get_source_info(name: str, rules: list[dict]):
    """
    分析指定name是否与某条规则匹配。如果符合匹配，则提取source、pid与metadata。
    :param name: 文件名部分
    :param rules: 识别规则
    :return: (str, str, dict[str, str]) or None
    """
    for rule in rules:
        matcher = rule["filename"].match(name)
        if matcher is not None:
            try:
                analysed_pid = matcher.group(rule.get("group") or 1)
                metadata = {}
                if rule.get("metadata") is not None:
                    for (g, field) in rule.get("metadata").items():
                        result = matcher.group(g)
                        if result is not None:
                            metadata[field] = result
                return rule["source"], analysed_pid, metadata
            except IndexError:
                raise IndexError("no such group. Name is '%s', rule is '%s', group id is '%s'." % (name, rule["filename"], rule.get("group") or 1))
    return None


def scan_move_files(work_dir: str, rules: list[dict], extensions: list[str]):
    """
    指定工作目录，然后按照规则识别出应该被移动的文件列表及其元数据。
    :param work_dir: 工作目录
    :param rules: 识别规则，结构参考config.yaml的save.rules
    :param extensions: 支持扫描的文件类型
    :return: (list[(str, str, str, dict[str, str])], list[str]) 给出(文件名, source, pid, metadata)的元组列表，和不匹配文件的列表
    """
    # 预处理规则
    rules = [{"filename": re.compile(rule["filename"]), "source": rule["source"], "group": rule.get("group"), "metadata": rule.get("metadata")} for rule in rules]
    # 扫描并过滤基本文件列表
    files: list[(str, str)] = __split_and_filter_extensions(__get_files_in_directory(work_dir), extensions)
    # 根据文件列表和规则清单匹配，分理出matched和unmatched项
    analyzed_files: list[(str, (str, str, dict[str, str]))] = [(__get_fullname(name, extension), __get_source_info(name, rules)) for (name, extension) in files]

    matched = [(filename, *s) for (filename, s) in analyzed_files if s is not None]
    unmatched = [filename for (filename, s) in analyzed_files if s is None]

    return matched, unmatched


def do_move_files(work_dir: str, target_dir: str, move_list: list[str]):
    """
    执行移动计划。
    """
    try:
        os.makedirs(target_dir)
    except FileExistsError:
        pass
    for filename in move_list:
        os.rename(os.path.join(work_dir, filename), os.path.join(target_dir, filename))


def do_delete_files(work_dir: str, delete_list: list[(str, str)]):
    """
    执行删除计划。
    """
    for (folder, filename) in delete_list:
        try:
            os.remove(os.path.join(work_dir, folder, filename))
        except FileNotFoundError:
            pass


def scan_folders(archive_dir: str):
    """
    指定归档目录，扫描其中的子目录列表。
    :param archive_dir: 归档目录
    :return: list[str]
    """
    return [f.name for f in os.scandir(archive_dir) if f.is_dir()]


def scan_not_existing_files(work_dir: str, files: list[str]):
    """
    扫描指定工作目录，根据给定的文件清单，查找工作目录中不存在的文件项。
    :param work_dir: 工作目录
    :param files: 文件清单
    :return: list[str]
    """
    filenames = set(f.name for f in os.scandir(work_dir) if not f.is_dir())
    return [f for f in files if f not in filenames]


if __name__ == '__main__':
    rr = scan_rename_files("/home/heer/Pictures/收图", [
        {
            "filename": '^(\\d+_p\\d+)$',
            "rename": 'pixiv_{1}'
        }
    ], ['jpg', 'jpeg', 'png', 'gif', 'webm', 'mp4'], ['^sankakucomplex_\\d+$', '^pixiv_\\d+_p\\d+$'])
    import json
    print(json.dumps(rr, indent=2))
