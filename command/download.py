from module.database import Database, get_analyzable_records
from module.external import External, available_types
from module.config import load_conf
from datetime import datetime
import time


def download():
    """
    搜索数据库中未解析且能解析的项，爬取它们的元数据详情，并填入数据库。
    """
    conf = load_conf()
    db = Database(conf["work_path"]["db_path"])
    external = External(conf["download"].get("strategy", {}), conf["download"].get("params", {}))
    waiting_interval = conf["download"].get("waiting_interval", 0)

    records = get_analyzable_records(db, available_types)
    if len(records) <= 0:
        print("# 发现0条可解析的记录")
        return

    print("# 发现%s条可解析的记录，开始元数据解析" % (len(records),))
    print()

    begin_download_time = datetime.now()
    header_printer = download_header_printer(len(records))
    last_download_time = None
    success_num, failed_num = 0, 0
    for index, (source, pid) in enumerate(records):
        if waiting_interval > 0:
            if last_download_time is not None:
                total_seconds = (datetime.now() - last_download_time).total_seconds()
                if total_seconds < waiting_interval:
                    try:
                        time.sleep(waiting_interval - total_seconds)
                    except InterruptedError or KeyboardInterrupt:
                        print("# 解析中止")
                        break
            last_download_time = datetime.now()
        try:
            result, try_time, try_count, err = external.get(source).post(pid)
        except InterruptedError or KeyboardInterrupt:
            print("# 解析中止")
            break

        header_printer(index, source, pid, try_count, try_time, err)
        if err is not None:
            db.write_error_status(source, pid)
            failed_num += 1
        else:
            relations = {'pools': result['pools'], 'parent': result['parent'], 'children': result['children']}
            meta = {'source': result['source'], 'rating': result['rating'], 'md5': result['md5']}
            db.write_metadata(source, pid, result['tags'], relations, meta)
            success_num += 1

    end_download_time = datetime.now()
    print()
    print('# 解析结束，共耗时%s。解析成功\033[1;32m%d\033[0m项，解析失败\033[1;31m%d\033[0m项' % (get_sum_time_cost(begin_download_time, end_download_time), success_num, failed_num))


def download_header_printer(count: int):
    count_len = len(str(count))

    def print_header(i: int, source: str, pid: str, try_count: int or None, try_time: int or None, err: str or None):
        print(("%s | %" + str(count_len) + "s/%s ") % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), i + 1, count), end="")
        print("\033[1;33m| %8s | %-12s |\033[0m" % (source, pid), end="")
        if err is not None:
            print('\033[1;31m Failed  (try %s time(s) in %.2fs): %s\033[0m' % (try_count, try_time, err))
        else:
            print('\033[1;32m Success (try %s time(s) in %.2fs)\033[0m' % (try_count, try_time))
    return print_header


def get_sum_time_cost(begin, end):
    t = (end - begin).seconds
    second = t % 60
    minute = t // 60
    hour = minute // 60
    minute = minute % 60
    if hour > 0:
        return "%02d:%02d:%02d" % (hour, minute, second)
    else:
        return "%02d:%02d" % (minute, second)
