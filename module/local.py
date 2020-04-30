import os
import re
import xattr
import biplist


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
            os.rename(os.path.join(self.__base, folder_name, old_name), os.path.join(self.__base, folder_name, new_name))
            return True
        except Exception:
            return False



if __name__ == '__main__':
    local = Local(
        path='/Users/heer/Library/Application Support/Hedge/Image Database',
        strategy={
            'complex': {
                'scan': 'sankakucomplex_(\\d+)',
                'refer': 'https://chan.sankakucomplex.com/post/show/(\\d+)',
                'rename': 'sankakucomplex_{0}.{extension}'
            },
            'pixiv': {
                'scan': 'pixiv_(\\d+_p\\d+)',
                'refer': 'https://www.pixiv.net/artworks/(\\d+)',
                'rename': 'pixiv_{filename/.*?(\\d+_p\\d+)/0}.{extension}'
            },
            'konachan': {
                'scan': 'Konachan.com - (\\d+)',
                'refer': 'https://konachan.com/post/show/(\\d+)',
                'rename': 'konachan_{0}.{extension}'
            }
        },
        types=['jpg', 'jpeg', 'png', 'gif', 'webm', 'mp4']
    )
    res = local.refer('2020-04-10')
    print('need rename:')
    for r in res['result']:
        if r['filename'] != r['rename']:
            print(r)
    print('failed:')
    for f in res['failed']:
        print(f)
    # local.rename('Downloaded', [(r['filename'], r['rename']) for r in res['result'] if r['filename'] != r['rename']])
