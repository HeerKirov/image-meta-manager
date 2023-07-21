import sqlite3
import json
import datetime


class STATUS:
    NOT_ANALYSED = 0
    ANALYSED = 1
    ERROR = 2


def status_to_index(status):
    if status == 'analysed':
        return 1
    elif status == 'not-analysed':
        return 0
    else:
        return 2


def index_to_status(index):
    return ['NOT_ANALYSED', 'ANALYSED', 'ERROR'][index]


class Database:
    def __init__(self, path):
        self.__conn = sqlite3.connect(path)
        self.__initialize()

    def __initialize(self):
        cursor = self.__conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS meta(
            id INTEGER PRIMARY KEY,
            status TINYINT NOT NULL,
            folder TEXT NULL,
            filename TEXT NOT NULL,
            
            source VARCHAR(16) NOT NULL,
            pid VARCHAR(16) NOT NULL,
            
            tags TEXT NULL,
            relations TEXT NULL,
            meta TEXT NULL,
            
            deleted BOOLEAN NOT NULL DEFAULT FALSE,
            create_time TIMESTAMP NOT NULL,
            analyse_time TIMESTAMP NULL DEFAULT NULL
        )''')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS meta_source_pid ON meta(source, pid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS meta_analyse_status ON meta(source, status)')
        cursor.close()
        self.__conn.commit()

    def close(self):
        self.__conn.close()

    def cursor(self):
        return self.__conn.cursor()

    def query_basic(self, source, pid):
        cursor = self.__conn.cursor()
        try:
            result = cursor.execute('SELECT folder, filename FROM meta WHERE source = ? AND pid = ?', (source, pid)).fetchone()
            if result is None:
                return None
            return result
        finally:
            cursor.close()

    def query_one(self, source, pid):
        cursor = self.__conn.cursor()
        try:
            result = cursor.execute('SELECT status, folder, filename, tags, relations, meta, create_time, analyse_time '
                                    'FROM meta WHERE source = ? AND pid = ?', (source, pid)).fetchone()
            if result is None:
                return None
            status, folder, filename, tags, relations, meta, create_time, analyse_time = result
            return {
                'source': source,
                'pid': pid,
                'status': index_to_status(status),
                'folder': folder,
                'filename': filename,
                'tags': json.loads(tags) if tags is not None else None,
                'relations': json.loads(relations) if relations is not None else None,
                'meta': json.load(meta) if meta is not None else None,
                'create_time': create_time,
                'analyse_time': analyse_time
            }
        finally:
            cursor.close()

    def query_list(self, folder=None, filename=None, source_in=None, status_in=None,
                   create_from=None, analyse_from=None, order=None, limit=None):
        sql = 'SELECT source, pid, status, folder, filename, tags, relations, meta, create_time, analyse_time FROM meta'
        parameters = []

        wheres = []
        if folder is not None:
            wheres.append('folder LIKE ?')
            parameters.append(folder)
        if filename is not None:
            wheres.append('filename LIKE ?')
            parameters.append(filename)
        if source_in is not None and len(source_in) > 0:
            wheres.append('source IN (' + ', '.join(['?'] * len(source_in)) + ')')
            parameters += source_in
        if status_in is not None and len(status_in) > 0:
            wheres.append('status IN (' + ', '.join(['?'] * len(status_in)) + ')')
            parameters += [str(status_to_index(i)) for i in status_in]
        if create_from is not None:
            wheres.append('create_time > ?')
            parameters.append(create_from)
        if analyse_from is not None:
            wheres.append('analyse_time > ?')
            parameters.append(analyse_from)
        wheres.append('(NOT deleted)')
        if len(wheres) > 0:
            sql += ' WHERE ' + ' AND '.join(wheres)

        if order is not None and len(order) > 0:
            orders = []
            for o in order:
                if o.startswith('-'):
                    orders.append(o[1:].replace('-', '_') + ' DESC')
                else:
                    orders.append(o.replace('-', '_'))
            sql += ' ORDER BY ' + ', '.join(orders)

        if limit is not None:
            sql += ' LIMIT ?'
            parameters.append(limit)

        cursor = self.__conn.cursor()
        try:
            result = cursor.execute(sql, parameters).fetchall()
            ret = []
            for res in result:
                source, pid, status, folder, filename, tags, relations, meta, create_time, analyse_time = res
                ret.append({
                    'source': source,
                    'pid': pid,
                    'status': index_to_status(status),
                    'folder': folder,
                    'filename': filename,
                    'tags': json.loads(tags) if tags is not None else None,
                    'relations': json.loads(relations) if relations is not None else None,
                    'meta': json.loads(meta) if meta is not None else None,
                    'create_time': create_time,
                    'analyse_time': analyse_time
                })
            return ret
        finally:
            cursor.close()

    def query_folders(self):
        cursor = self.__conn.cursor()
        try:
            result = cursor.execute('SELECT folder FROM meta GROUP BY folder ORDER BY folder').fetchall()
            return [f for (f,) in result]
        finally:
            cursor.close()

    def query_folder_filenames(self, folder):
        cursor = self.__conn.cursor()
        try:
            result = cursor.execute('SELECT filename FROM meta WHERE folder = ? AND NOT deleted', (folder,)).fetchall()
            return [f for (f,) in result]
        finally:
            cursor.close()

    def insert(self, source, pid, folder: str = None, filename: str = None, metadata: dict[str, str] = None, replace=True):
        cursor = self.__conn.cursor()
        try:
            result = cursor.execute('SELECT id, meta FROM meta WHERE source = ? AND pid = ? LIMIT 1', (source, pid)).fetchone()
            if result is not None:
                if replace:
                    (_, old_metadata) = result
                    if metadata is not None and len(metadata) > 0:
                        new_metadata = json.loads(old_metadata) if old_metadata is not None else {}
                        for (k, v) in metadata.items():
                            new_metadata[k] = v
                        cursor.execute(
                            'UPDATE meta SET folder = ?, filename = ?, create_time = ?, meta = ?, deleted = FALSE WHERE source = ? AND pid = ?',
                            (folder, filename, datetime.datetime.now(), json.dumps(new_metadata), source, pid))
                    else:
                        cursor.execute(
                            'UPDATE meta SET folder = ?, filename = ?, create_time = ?, deleted = FALSE WHERE source = ? AND pid = ?',
                            (folder, filename, datetime.datetime.now(), source, pid))
                return False
            else:
                cursor.execute('INSERT INTO meta(status, folder, filename, source, pid, tags, relations, meta, create_time)VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                               (STATUS.NOT_ANALYSED, folder, filename, source, pid,
                                None, None, json.dumps(metadata) if metadata is not None else None, datetime.datetime.now()))
                return True
        finally:
            cursor.close()
            self.__conn.commit()

    def write_only_meta(self, source, pid, meta):
        cursor = self.__conn.cursor()
        try:
            cursor.execute('UPDATE meta SET meta = ?, analyse_time = ?, deleted = FALSE WHERE source = ? AND pid = ?',
                           (json.dumps(meta) if meta is not None else None, datetime.datetime.now(), source, pid))
        finally:
            cursor.close()
            self.__conn.commit()

    def write_metadata(self, source, pid, tags, relations, meta):
        cursor = self.__conn.cursor()
        try:
            cursor.execute('UPDATE meta SET status = ?, tags = ?, relations = ?, meta = ?, analyse_time = ?, deleted = FALSE '
                           'WHERE source = ? AND pid = ?',
                           (STATUS.ANALYSED,
                            json.dumps(tags) if tags is not None else None,
                            json.dumps(relations) if relations is not None else None,
                            json.dumps(meta) if meta is not None else None,
                            datetime.datetime.now(),
                            source, pid))
        finally:
            cursor.close()
            self.__conn.commit()

    def mark_deleted(self, folder, filename):
        cursor = self.__conn.cursor()
        try:
            cursor.execute('UPDATE meta SET deleted = TRUE WHERE folder = ? AND filename = ?', (folder, filename))
        finally:
            cursor.close()
            self.__conn.commit()

    def write_error_status(self, source, pid):
        cursor = self.__conn.cursor()
        try:
            cursor.execute('UPDATE meta SET status = ?, analyse_time = ?, deleted = FALSE WHERE source = ? AND pid = ?',
                           (STATUS.ERROR, datetime.datetime.now(), source, pid))
        finally:
            cursor.close()
            self.__conn.commit()


def scan_record_existence(db: Database, files: list[(str, str, str, dict[str, str])]):
    """
    扫描指定的文件列表，是否在数据库中已有重复项。判断的依据是source和pid。
    :return: list[(str, str, str, dict[str, str])], list[(str, str, str, dict[str, str], str, str)] 不存在的列表，和重复存在的列表
    """
    exists, not_exists = [], []
    for (filename, source, pid, metadata) in files:
        ex = db.query_basic(source, pid)
        if ex is not None:
            exists.append((filename, source, pid, metadata, *ex))
        else:
            not_exists.append((filename, source, pid, metadata))

    return not_exists, exists


def insert_records(db: Database, folder: str, files: list[(str, str, str, dict[str, str])]):
    """
    将指定的文件信息存入数据库。
    """
    for (filename, source, pid, metadata) in files:
        db.insert(source, pid, folder=folder, filename=filename, metadata=metadata, replace=True)


def get_analyzable_records(db: Database, source: list[str]):
    """
    查询所有可分析的记录列表。
    """
    return [(item["source"], item["pid"]) for item in db.query_list(status_in=['not-analysed', 'error'], source_in=source, order=['create-time'])]


def analyze_tag_types(db: Database, source: str):
    """
    分析现有数据的tag type的分布情况。
    """
    cursor = db.cursor()
    try:
        fetch = cursor.execute('SELECT source, tags FROM meta WHERE source = ?', (source,)).fetchall()

        # name -> type
        tag_type: dict[str, str] = dict()
        # name -> count
        tag_count: dict[str, int] = dict()
        for record in fetch:
            source, tags_str = record
            if tags_str is not None:
                tags = json.loads(tags_str)
                for tag in tags:
                    name = tag['name']
                    tp = tag['type']
                    tag_count[name] = tag_count[name] + 1 if name in tag_count else 1
                    if name not in tag_type:
                        tag_type[name] = tp

        # type -> count(tag)
        type_count: dict[str, int] = dict()
        for tp in tag_type.values():
            type_count[tp] = type_count[tp] + 1 if tp in type_count else 1
    finally:
        cursor.close()

    return type_count


def get_tag_of_type(db: Database, source: str, tag_type: str):
    cursor = db.cursor()
    try:
        fetch = cursor.execute('SELECT source, tags FROM meta WHERE source = ?', (source,)).fetchall()

        # name -> count
        tag_count: dict[str, int] = dict()
        no_this_tag = 0
        cnt = 0
        for record in fetch:
            source, tags_str = record
            if tags_str is not None:
                tags = json.loads(tags_str)
                any_this_tag = False
                for tag in tags:
                    name = tag['name']
                    tp = tag['type']
                    if tp == tag_type:
                        tag_count[name] = tag_count[name] + 1 if name in tag_count else 1
                        any_this_tag = True
                if not any_this_tag:
                    no_this_tag += 1
            cnt += 1
    finally:
        cursor.close()

    return sorted(tag_count.items(), key=lambda x: (x[1], x[0])), no_this_tag, cnt


if __name__ == '__main__':
    d = Database('/home/heer/.config/imm/data.db')
    r, ntt, c = get_tag_of_type(d, 'complex', 'copyright')
    for i in r:
        print("%-56s: %d" % i)
    print("%-56s: %d" % ("no this tag type", ntt))
    print("%-56s: %d" % ("[all count]", c))
