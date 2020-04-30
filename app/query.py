from .environment import database, external
from datetime import datetime
import time


def query_one(actions, flags, _):
    source = actions['source']
    pid = actions['pid']
    item = database().query_one(source, pid)
    if item is None:
        print('\033[1;31m%s - %s not found\033[0m' % (source, pid))
        return
    print('\033[1;34m-- %s - %s (%s) --\033[0m' % (source, pid, item['status']))
    if flags['download']:
        result, try_time, try_count, err = external(source).post(pid)
        if err is not None:
            print('\033[1;31mmeta download failed: %s\033[0m' % (err,))
            print('\033[1;33mtry %s time(s) in %.2fs\033[0m' % (try_count, try_time))
            database().update_error(source, pid)
            return
        database().update(source, pid,
                          result['tags'],
                          {'pools': result['pools'], 'parent': result['parent'], 'children': result['children']},
                          None)
        item = database().query_one(source, pid)
        print('\033[1;33mtry %s time(s) in %.2fs\033[0m' % (try_count, try_time))
    print_all = flags['all']
    if item['tags'] is not None:
        __print_tags(item['tags'], print_all)
    if item['relations'] is not None:
        __print_relations(item['relations'])


def query_list(_, flags, params):
    items = database().query_list(folder=params.get('folder'), filename=params.get('filename'),
                                  source_in=params.get('source'), status_in=params.get('status'),
                                  create_from=params.get('create-from'), analyse_from=params.get('analyse-from'),
                                  order=params.get('order'), limit=params.get('limit'))
    print('\033[1;34m-- %s --\033[0m' % ('download' if flags['download'] else 'query',))
    count = len(items)
    count_len = len(str(count))
    count_template = '| %%%ds/%%s ' % (count_len,)
    interval = params['interval']
    last_download_time = None
    for index, item in enumerate(items):
        if flags['download']:
            print(count_template % (index + 1, count), end='')
        print('\033[1;33m| %8s | %-12s |\033[0m %-12s/ %-30s | %-12s |' %
              (item['source'], item['pid'], item['folder'], item['filename'], item['status']), end='')
        if flags['download']:
            if interval > 0:
                if last_download_time is not None:
                    total_seconds = (datetime.now() - last_download_time).total_seconds()
                    if total_seconds < interval:
                        time.sleep(interval - total_seconds)
                last_download_time = datetime.now()
            result, try_time, try_count, err = external(item['source']).post(item['pid'])
            if err is not None:
                database().update_error(item['source'], item['pid'])
                print('\033[1;31m download failed: %s (try %s time(s) in %.2fs)\033[0m' % (err, try_count, try_time))
            else:
                database().update(item['source'], item['pid'],
                                  result['tags'], {
                                      'pools': result['pools'],
                                      'parent': result['parent'],
                                      'children': result['children']
                                  }, None)
                print('\033[1;32m download success (try %s time(s) in %.2fs)\033[0m' % (try_count, try_time))
        else:
            __print_contains(item['tags'] or [], item['relations'] or {})
    print('\033[1;34m-- %s item(s) --\033[0m' % (len(items),))


def __print_tags(tags, print_all):
    print('\033[1;36m-- tags:\033[0m')
    types = dict()
    for tag in tags:
        if tag['type'] not in types:
            types[tag['type']] = [tag]
        else:
            types[tag['type']].append(tag)
    for t, a in types.items():
        print('\033[1;32m - %s:\033[0m' % (t,))
        for tag in (a if print_all else a[:8]):
            print('   %s %s' % (tag['name'], '[' + tag['title'] + ']' if tag.get('title') else ''))
        if not print_all and len(a) > 8:
            print('   ...')


def __print_relations(relations):
    print('\033[1;36m-- relations:\033[0m')
    if relations['pools']:
        print('\033[1;32m - pools:\033[0m')
        for pool in relations['pools']:
            print('   %s' % (pool,))
    if relations['parent']:
        print('\033[1;32m - parent: \033[0m%s' % (', '.join(relations['parent']),))
    if relations['children']:
        print('\033[1;32m - children:\033[0m')
        for child in relations['children']:
            print('   %s' % (child,))


def __print_contains(tags, relations):
    types = dict()
    for tag in tags:
        if tag['type'] not in types:
            types[tag['type']] = 1
        else:
            types[tag['type']] += 1
    print('\033[1;32m tags[%s], pools(%d), parent(%d), children(%d)\033[0m' %
          (', '.join('%s(%d)' % (tag, count) for tag, count in types.items()),
           len(relations.get('pools', [])), len(relations.get('parent', [])), len(relations.get('children', []))))
