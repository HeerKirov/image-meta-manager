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
            
            create_time TIMESTAMP NOT NULL,
            analyse_time TIMESTAMP NULL DEFAULT NULL
        )''')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS meta_source_pid ON meta(source, pid)')
        cursor.close()
        self.__conn.commit()

    def close(self):
        self.__conn.close()

    def exist(self, source, pid):
        cursor = self.__conn.cursor()
        try:
            return cursor.execute('SELECT count(1) FROM meta WHERE source = ? AND pid = ?', (source, pid))\
                       .fetchone()[0] > 0
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

    def query_list(self,
                   folder=None, filename=None, source_in=None, status_in=None,
                   create_from=None, analyse_from=None,
                   order=None, limit=None):
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
                    'meta': json.load(meta) if meta is not None else None,
                    'create_time': create_time,
                    'analyse_time': analyse_time
                })
            return ret
        finally:
            cursor.close()

    def create(self, source, pid, folder=None, filename=None, replace=True):
        cursor = self.__conn.cursor()
        try:
            if cursor.execute('SELECT count(1) FROM meta WHERE source = ? AND pid = ?', (source, pid))\
                       .fetchone()[0] > 0:
                if replace:
                    cursor.execute('UPDATE meta SET folder = ?, filename = ?, create_time = ? '
                                   'WHERE source = ? AND pid = ?',
                                   (folder, filename, datetime.datetime.now(), source, pid))
                return False
            else:
                cursor.execute('INSERT INTO meta(status, folder, filename, source, pid, '
                               'tags, relations, meta, create_time) '
                               'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                               (STATUS.NOT_ANALYSED, folder, filename, source, pid,
                                None, None, None, datetime.datetime.now()))
                return True
        finally:
            cursor.close()
            self.__conn.commit()

    def update(self, source, pid, tags, relations, meta):
        cursor = self.__conn.cursor()
        try:
            cursor.execute('UPDATE meta SET status = ?, tags = ?, relations = ?, meta = ?, analyse_time = ? '
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

    def update_error(self, source, pid):
        cursor = self.__conn.cursor()
        try:
            cursor.execute('UPDATE meta SET status = ?, analyse_time = ? WHERE source = ? AND pid = ?',
                           (STATUS.ERROR, datetime.datetime.now(), source, pid))
        finally:
            cursor.close()
            self.__conn.commit()
