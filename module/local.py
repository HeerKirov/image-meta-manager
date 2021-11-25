import os
import re
import xattr
import biplist
import datetime


def default_scan_transform(strategy_name, filename, groups, meta):
    """
    默认的scan扫描时，将匹配成功的文件解析为元信息的回调。
    :param strategy_name: 策略模式名
    :param filename: 文件名
    :param groups: 正则匹配的groups结果
    :param meta: 此策略模式的元信息
    :return: {'source', 'pid', 'filename'}
    """
    return {'source': strategy_name, 'pid': groups[0], 'filename': filename}


def default_refer_transform(strategy_name, filename, refer_name, groups, meta):
    """
    默认的refer扫描时，将匹配成功的来源信息解析为文件名的回调。
    :param strategy_name: 策略模式名
    :param filename: 原文件名
    :param refer_name: 来源
    :param groups: 正则匹配的groups结果
    :param meta: 此策略模式的元信息
    :return: 文件名，含扩展名
    """
    template = meta['rename']
    while True:
        start, end, pattern = get_next_pattern(template)
        if pattern is None:
            return template
        elif len(pattern) != 1 and len(pattern) != 3:
            raise Exception('wrong rename template \'%s\'.' % (meta['rename'],))
        if pattern[0].isdigit():
            value = groups[int(pattern[0])]
        elif pattern[0] == 'filename':
            value = filename
        elif pattern[0] == 'refer':
            value = refer_name
        elif pattern[0] == 'extension' or pattern[0] == 'ext':
            value = get_extension(filename) or ''
        else:
            raise Exception('unknown template variable \'%s\'.' % (pattern[0],))
        if len(pattern) == 3:
            reg = re.compile(pattern[1])
            matcher = reg.match(value)
            if matcher is not None:
                value = matcher.groups()[int(pattern[2])]
        template = template[:start] + value + template[end + 1:]


def get_next_pattern(template, begin=0):
    start = template.find('{', begin)
    end = template.find('}', begin)
    if 0 <= start < end:
        return start, end, template[start + 1:end].split('/')
    return -1, -1, None


def get_extension(filename: str):
    p = filename.rfind('.')
    return filename[p + 1:] if p >= 0 else None


class Local:
    def __init__(self, path, strategy, types=None):
        self.__base = path
        self.__types = set(types) if types is not None else None
        self.__strategy = {}
        for k, v in strategy.items():
            self.__strategy[k] = {
                'scan': re.compile(v['scan']) if 'scan' in v else None,
                'scan.delegate': v.get('scan.delegate', default_scan_transform),
                'refer': re.compile(v['refer']) if 'refer' in v else None,
                'refer.delegate': v.get('refer.delegate', default_refer_transform),
                'meta': v
            }

    def folders(self, reg):
        rec = re.compile(reg)
        ret = []
        for top, dirs, non_dirs in os.walk(self.__base):
            for d in dirs:
                matcher = rec.match(d)
                if matcher is not None:
                    ret.append(d)
        ret.sort()
        return ret

    def scan(self, folder_name):
        """
        扫描指定文件夹下的指定文件，并给出它们的元定义信息。
        scan_type参数会过滤文件列表。不在此扩展名列表中的文件将不加入解析。
        :param folder_name: 文件夹名称
        :return: {
            result: [{'source', 'pid', 'filename'}] 给出所有解析成功的文件的元信息。解析策略通过参数scan_strategy给出。
            failed: [''] 找不到解析策略的文件。
        }
        """
        result = []
        failed = []
        for top, dirs, non_dirs in os.walk(os.path.join(self.__base, folder_name)):
            for item in non_dirs:
                if self.__types is not None and get_extension(item) not in self.__types:
                    continue
                for k, v in self.__strategy.items():
                    matcher = v['scan'].match(item)
                    if matcher is not None:
                        result.append(v['scan.delegate'](k, item, matcher.groups(), v['meta']))
                        break
                else:
                    failed.append(item)
        return {
            'result': result,
            'failed': failed
        }

    def refer(self, folder_name):
        """
        扫描一个文件夹下的所有文件，并根据其macOS meta 下载来源信息，配合来源策略，推断其命名是否正确。
        :param folder_name: 指定的文件夹名称
        :return: {
            'result': [{'filename', 'rename', 'refer'}] 给出解析成功的文件的来源信息，以及建议的命名。
            'failed': [''] 找不到解析策略的文件。
        }
        """
        result = []
        failed = []
        for top, dirs, non_dirs in os.walk(os.path.join(self.__base, folder_name)):
            for item in non_dirs:
                if self.__types is not None and get_extension(item) not in self.__types:
                    continue
                x = xattr.xattr(os.path.join(self.__base, folder_name, item))
                try:
                    where_froms_byte = x.get('com.apple.metadata:kMDItemWhereFroms')
                except OSError:
                    failed.append(item)
                    continue
                if where_froms_byte is None:
                    failed.append(item)
                    continue

                def for_froms():
                    where_froms = biplist.readPlistFromString(where_froms_byte)
                    for where_from in where_froms:
                        for k, v in self.__strategy.items():
                            matcher = v['refer'].match(where_from)
                            if matcher is not None:
                                return where_from, v['refer.delegate'](k, item, where_from, matcher.groups(), v['meta'])
                    return None, None

                refer_name, rename = for_froms()
                if refer_name is None or rename is None:
                    failed.append(item)
                    continue
                result.append({'filename': item, 'rename': rename, 'refer': refer_name})
        return {
            'result': result,
            'failed': failed
        }

    def rename(self, folder_name, old_name, new_name):
        """
        对一个文件夹下的文件进行重命名。
        :param folder_name: 目标文件夹
        :param old_name
        :param new_name
        :return 是否重命名失败
        """
        try:
            os.rename(os.path.join(self.__base, folder_name, old_name),
                      os.path.join(self.__base, folder_name, new_name))
            return True
        except Exception:
            return False


def get_today_archive(offset: int or None, split: int or None):
    now = datetime.datetime.now()
    if offset is not None:
        now = now - datetime.timedelta(hours=offset)
    return "%s.%s" % (now.strftime("%Y-%m-%d"), split) if split is not None else now.strftime("%Y-%m-%d")


def get_fullname(name: str, extension: str or None):
    return "%s.%s" % (name, extension) if extension is not None else name


def filter_into(li: list, condition):
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


def get_name_and_extension(filename: str):
    """
    取得指定文件的名称和扩展名部分。
    """
    p = filename.rfind('.')
    return (filename[:p], filename[p + 1:]) if p >= 0 else (filename, None)


def get_files_in_directory(directory: str):
    """
    扫描指定目录下的所有文件。
    :param directory: 目录位置
    :return: list[str] filenames
    """
    result = []
    for top, dirs, non_dirs in os.walk(directory):
        result.extend(non_dirs)
    return result


def split_and_filter_extensions(filenames: list[str], extensions: list[str]):
    result = []
    for filename in filenames:
        n, e = get_name_and_extension(filename)
        if extensions is None or e in extensions:
            result.append((n, e))
    return result


def next_pattern(template, begin=0):
    start = template.find('{', begin)
    end = template.find('}', begin)
    return (start, end, template[start + 1:end]) if 0 <= start < end else (-1, -1, None)


def replace_template(template: str, take):
    """
    将template中的占位符替换掉。
    :param template: 携带{}占位符的文本
    :param take: lambda表达式。根据参数决定替换内容。参数可能是索引int，也可能是命名组str
    :return: str
    """
    begin = 0
    while True:
        start, end, pattern = next_pattern(template, begin)
        if pattern is None:
            return template
        elif pattern.isdigit():
            value = take(int(pattern))
        else:
            value = take(pattern)
        template = template[:start] + value + template[end + 1:]
        begin = start + len(value)


def get_rename(name: str, rules: list[dict]):
    """
    根据规则，匹配得到重命名后的名称。如果没有匹配，返回None。
    """
    for rule in rules:
        matcher = rule["filename"].match(name)
        if matcher is not None:
            return replace_template(rule["rename"], lambda k: matcher.group(k))
    return None


def split_duplicated_names(renamed_files: list[(str, str, str)], other_files: set[str]):
    """
    搜索并分离出重名的文件。
    :param renamed_files: rename列表
    :param other_files: 其他文件列表，来自excluded/unmatched，与它们重名也算做重名文件。
    :return list[(str, str, str)], dict[str, list[str]] 给出无重名文件列表，和重名文件集，结构为{最终文件: 现有文件名列表}
    """
    # 重名字典，key是最终filename，value则是renamed list清单
    name_map: dict[str, (list[str], str, str)] = dict()
    for (name, extension, rename) in renamed_files:
        re_filename = get_fullname(rename, extension)
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
            duplicated[filename] = [*[get_fullname(name, extension) for name in names], filename]
        elif len(names) > 1:
            duplicated[filename] = [get_fullname(name, extension) for name in names]
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
    files: list[(str, str)] = split_and_filter_extensions(get_files_in_directory(work_dir), extensions)
    # 过滤掉exclude列表
    included_files, excluded_files = filter_into(files, lambda f: len([1 for e in excludes if e.match(f[0])]) <= 0)
    excluded: list[str] = [get_fullname(name, extension) for (name, extension) in excluded_files]
    # 根据文件列表生成重命名清单，然后过滤出unmatched列表和matched列表
    renamed_files: list[(str, str, str or None)] = [(name, extension, get_rename(name, rules)) for (name, extension) in included_files]
    matched_files, unmatched_files = filter_into(renamed_files, lambda t: t[2] is not None)
    unmatched: list[str] = [get_fullname(name, extension) for (name, extension, _) in unmatched_files]
    # 根据清单，将matched中的重名项过滤出来
    not_duplicated, duplicated = split_duplicated_names(matched_files, set(unmatched).union(set(excluded)))
    # 生成重命名计划列表
    renames = [(get_fullname(name, extension), get_fullname(rename, extension)) for (name, extension, rename) in not_duplicated]
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


def get_source_info(name: str, rules: list[dict]):
    """
    分析指定name是否与某条规则匹配。如果符合匹配，则提取source和pid。
    :param name: 文件名部分
    :param rules: 识别规则
    :return: (str, str) or None
    """
    for rule in rules:
        matcher = rule["filename"].match(name)
        if matcher is not None:
            return rule["source"], matcher.group(rule.get("group", 1))
    return None


def scan_move_files(work_dir: str, rules: list[dict], extensions: list[str]):
    """
    指定工作目录，然后按照规则识别出应该被移动的文件列表及其元数据。
    :param work_dir: 工作目录
    :param rules: 识别规则，结构参考config.yaml的save.rules
    :param extensions: 支持扫描的文件类型
    :return: (list[(str, str, str)], list[str]) 给出(文件名, source, pid)的元组列表，和不匹配文件的列表
    """
    # 预处理规则
    rules = [{"filename": re.compile(rule["filename"]), "source": rule["source"], "group": rule.get("group")} for rule in rules]
    # 扫描并过滤基本文件列表
    files: list[(str, str)] = split_and_filter_extensions(get_files_in_directory(work_dir), extensions)
    # 根据文件列表和规则清单匹配，分理出matched和unmatched项
    analyzed_files: list[(str, (str, str))] = [(get_fullname(name, extension), get_source_info(name, rules)) for (name, extension) in files]

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


if __name__ == '__main__':
    rr = scan_rename_files("/home/heer/Pictures/收图", [
        {
            "filename": '^(\\d+_p\\d+)$',
            "rename": 'pixiv_{1}'
        }
    ], ['jpg', 'jpeg', 'png', 'gif', 'webm', 'mp4'], ['^sankakucomplex_\\d+$', '^pixiv_\\d+_p\\d+$'])
    import json
    print(json.dumps(rr, indent=2))
