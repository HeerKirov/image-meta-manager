from .environment import local, database


def scan_dir(actions, _, __):
    for i in local().folders(actions['dir']):
        print(i)


def scan_file(actions, flags, params):
    db = database() if flags['save'] else None
    duplicate_strategy = params['duplicate']
    count, saved = 0, 0
    analyse_failed, save_msg = [], []
    for folder in local().folders(actions['dir']):
        result = local().scan(folder)
        analyse_failed += [folder + '/' + i for i in result['failed']]
        count += len(result['result'])
        for item in result['result']:
            print('%8s - %-12s %s/%s' % (item['source'], item['pid'], folder, item['filename']))
            if db is not None:
                if db.create(item['source'], item['pid'], folder, item['filename'],
                             replace=duplicate_strategy == 'replace'):
                    saved += 1
                elif duplicate_strategy == 'warn':
                    save_msg.append(('WARN', item['source'], item['pid'], folder, item['filename']))
                else:
                    save_msg.append(('REPLACE', item['source'], item['pid'], folder, item['filename']))
    if len(save_msg) > 0:
        print('\033[1;33m-- save data notice --\033[0m')
        for t, source, pid, folder, filename in save_msg:
            if t == 'REPLACE':
                print('\033[33m%8s - %-12s is DUPLICATED then \033[35mREPLACED\033[33m (current file: %s/%s)\033[0m' %
                      (source, pid, folder, filename))
            else:
                print('\033[33m%8s - %-12s is DUPLICATED (current file: %s/%s)\033[0m' %
                      (source, pid, folder, filename))
    if len(analyse_failed) > 0:
        print('\033[1;31m-- analyse failed file --\033[0m')
        for item in analyse_failed:
            print('\033[31m%s\033[0m' % (item,))
    print('\033[1;36m-- analysed %s file; failed %s file --\033[0m' % (count, len(analyse_failed)))
    if db is not None:
        print('\033[1;36m-- save %s data; conflict %s data --\033[0m' % (saved, len(save_msg)))


def scan_refer(actions, flags, _):
    analyse_failed, rename_failed = [], []
    total, renamed = 0, 0

    print('\033[1;34m-- analysed file --\033[0m')
    for folder in local().folders(actions['dir']):
        result = local().refer(folder)
        analyse_failed += [folder + '/' + i for i in result['failed']]
        items = result['result'] if flags['all'] else [i for i in result['result'] if i['filename'] != i['rename']]
        total += len(items)
        for item in items:
            print('%s / %s -> %s' % (folder, item['filename'], item['rename']))
            if flags['rename'] and item['filename'] != item['rename']:
                if local().rename(folder, item['filename'], item['rename']):
                    renamed += 1
                else:
                    rename_failed.append((folder, item['filename'], item['rename']))
    if len(rename_failed) > 0:
        print('\033[1;33m-- rename failed file --\033[0m')
        for item in rename_failed:
            print('\033[31m%s / %s -/-> %s\033[0m' % item)
    if len(analyse_failed) > 0:
        print('\033[1;31m-- analyse failed file --\033[0m')
        for item in analyse_failed:
            print('\033[31m%s\033[0m' % (item,))
    print('\033[1;36m-- analysed %s file; failed %s file --\033[0m' % (total, len(analyse_failed)))
    if flags['rename']:
        print('\033[1;36m-- renamed %s file; failed %s file --\033[0m' % (renamed, len(rename_failed)))
