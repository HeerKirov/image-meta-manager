import json

from module.database import Database


db = Database('/home/heer/.config/imm/data.db')


def statistic_tag_type():
    types_count = dict()
    cursor = db.cursor()
    try:
        records = cursor.execute('SELECT tags FROM meta WHERE NOT deleted').fetchall()
        for (tags_str,) in records:
            if tags_str is not None and len(tags_str) > 0:
                tags = json.loads(tags_str)
                for tag in tags:
                    tag_name = tag["name"]
                    tag_type = tag["type"]
                    tag_set = types_count.get(tag_type)
                    if tag_set is None:
                        tag_set = set()
                        types_count[tag_type] = tag_set
                    tag_set.add(tag_name)
    except Exception:
        cursor.close()

    for k, v in types_count.items():
        print("%s: %s" % (k, len(v)))


def statistic_tag_count(tag_type: str):
    # copyright, character, artist, studio, general, meta, genre, medium
    tag_count: dict[str, int] = dict()
    tag_titles: dict[str, str] = dict()
    cursor = db.cursor()
    try:
        records = cursor.execute('SELECT tags FROM meta WHERE NOT deleted').fetchall()
        for (tags_str,) in records:
            if tags_str is not None and len(tags_str) > 0:
                tags = json.loads(tags_str)
                for tag in tags:
                    if tag["type"] == tag_type:
                        tag_name = tag["name"]
                        tag_title = tag["title"]
                        if tag_name in tag_count:
                            tag_count[tag_name] = tag_count[tag_name] + 1
                        else:
                            tag_count[tag_name] = 1
                        if tag_name not in tag_titles and tag_title is not None:
                            tag_titles[tag_name] = tag_title
    finally:
        cursor.close()

    tag_count_list = [t for t in tag_count.items()]
    tag_count_list.sort(key=lambda t: t[1])

    for k, v in tag_count_list:
        title = tag_titles.get(k)
        print("%-50s: %4d : %s" % (k, v, title or ""))


def statistic_tag_count_with_belongs(parent_type: str, child_type: str):
    parent_tag_count_map: dict[str, int] = dict()
    child_tag_count_map: dict[str, int] = dict()
    tag_titles_map: dict[str, str] = dict()
    tag_parent_count_map: dict[str, dict[str, int]] = dict()

    def add_parent_count(name: str):
        if name in parent_tag_count_map:
            parent_tag_count_map[name] = parent_tag_count_map[name] + 1
        else:
            parent_tag_count_map[name] = 1

    def add_child_count(name: str):
        if name in child_tag_count_map:
            child_tag_count_map[name] = child_tag_count_map[name] + 1
        else:
            child_tag_count_map[name] = 1

    def add_title(name: str, title: str or None):
        if name not in tag_titles_map and title is not None:
            tag_titles_map[name] = title

    def add_parents(name: str, parents: list[str]):
        if name in tag_parent_count_map:
            count_map = tag_parent_count_map[name]
        else:
            count_map = dict()
            tag_parent_count_map[name] = count_map
        for parent in parents:
            if parent in count_map:
                count_map[parent] = count_map[parent] + 1
            else:
                count_map[parent] = 1

    def sorted_items(d: iter):
        li = [t for t in d]
        li.sort(key=lambda t: t[1])
        return li

    def compute_if_absent(d: dict[str, any], key: str, generator):
        if key in d:
            return d[key]
        else:
            r = generator(key)
            d[key] = r
            return r

    cursor = db.cursor()
    try:
        records = cursor.execute('SELECT tags FROM meta').fetchall()
        for (tags_str,) in records:
            if tags_str is not None and len(tags_str) > 0:
                tags = json.loads(tags_str)
                current_parent_tags = []
                current_child_tags = []
                for tag in tags:
                    tag_name = tag["name"]
                    tag_title = tag["title"]
                    tag_type = tag["type"]
                    if tag_name == 'original' or tag_name == 'original character':
                        continue
                    if tag_type == parent_type:
                        add_parent_count(tag_name)
                        add_title(tag_name, tag_title)
                        current_parent_tags.append(tag_name)
                    elif tag_type == child_type:
                        add_child_count(tag_name)
                        add_title(tag_name, tag_title)
                        current_child_tags.append(tag_name)
                if len(current_child_tags) > 0 and len(current_parent_tags) > 0:
                    for child in current_child_tags:
                        add_parents(child, current_parent_tags)
    finally:
        cursor.close()

    # 准备以parent为key构造children列表
    tag_children_map: dict[str, set[str]] = dict()
    used_children: set[str] = set()
    for tag_name, tag_parents in tag_parent_count_map.items():
        if len(tag_parents) > 0:
            tag_parents = sorted_items(tag_parents.items())
            cnt = tag_parents[-1][1]
            # 选出出现频率多的parent,然后再根据parent的全局计数选出最少的那个parent使用
            tag_parents = [(n, parent_tag_count_map.get(n)) for (n, c) in tag_parents if c == cnt]
            tag_parents.sort(key=lambda t: t[1])
            selected_parent_name = tag_parents[0][0]
            s = compute_if_absent(tag_children_map, selected_parent_name, lambda p: set())
            s.add(tag_name)
            used_children.add(tag_name)
    # 没有parent的children列表
    no_parent_children: set[str] = set(n for (n, _) in child_tag_count_map.items() if n not in used_children)

    def print_children(children: set[str] or None):
        if children is not None and len(children) > 0:
            for n, c in sorted_items((n, c) for (n, c) in child_tag_count_map.items() if n in children):
                t = tag_titles_map.get(n)
                print("        %-42s: %4d : %s" % (n, c, t or ""))

    # 将parent tag按照count升序排列，然后开始打印
    for tag_name, tag_count in sorted_items(parent_tag_count_map.items()):
        tag_title = tag_titles_map.get(tag_name)
        children_name_list = tag_children_map.get(tag_name, None)
        children_count = len(children_name_list) if children_name_list is not None else 0
        print("%-50s: %4d : %s" % ("%s (%d)" % (tag_name, children_count), tag_count, tag_title or ""))
        # 然后升序打印所有children
        print_children(children_name_list)
    print("NO PARENT:")
    print_children(no_parent_children)


if __name__ == '__main__':
    statistic_tag_count_with_belongs("copyright", "character")
