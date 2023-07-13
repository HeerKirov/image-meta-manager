from module.local import scan_move_files, do_delete_files, scan_folders, scan_not_existing_files
from module.database import Database, insert_records
from module.config import load_conf
import os


def organize(deduplicate, unsaved, mark_deleted, dry_run):
    """
    进行文件存储和数据库整理。
    :param deduplicate: 移除文件库中的重复文件，以最后一次存档为准
    :param unsaved: 查找文件库中的未保存文件
    :param mark_deleted: 搜索并在数据库中标记已被删除的文件
    :param dry_run: 试运行，生成并打印执行计划，但不实际执行计划
    """
    conf = load_conf()
    db = Database(conf["work_path"]["db_path"])

    print("# 文件整理")
    if not unsaved and not deduplicate and not mark_deleted:
        print("# \033[1;31m未指定任何整理项。\033[0m")

    if unsaved:
        __unsaved(conf, db, dry_run)
    if deduplicate:
        __deduplicate(conf, db, dry_run)
    if mark_deleted:
        __mark_deleted(conf, db, dry_run)


def __unsaved(conf, db: Database, dry_run: bool):
    unsaved_files = []
    all_folders = scan_folders(conf["work_path"]["archive_dir"])
    for folder in all_folders:
        matched_files, unmatched_files = scan_move_files(
            work_dir=os.path.join(conf["work_path"]["archive_dir"], folder),
            rules=conf["save"]["rules"],
            extensions=conf.get("supported_extensions")
        )

        for filename, source, pid, _ in matched_files:
            r = db.query_basic(source, pid)
            if r is None:
                # 遭遇未保存的意外文件
                unsaved_files.append((folder, filename, source, pid))

    print()
    if len(unsaved_files) > 0:
        print("# === 发现未保存项 %s项 ===" % (len(unsaved_files),))
        for folder, filename, _, _ in unsaved_files:
            print("* \033[1;33m%-12s / %-30s\033[0m" % (folder, filename))

        if not dry_run:
            grouped_files = dict()
            for folder, filename, source, pid in unsaved_files:
                if folder in grouped_files:
                    grouped_files[folder].append((filename, source, pid))
                else:
                    grouped_files[folder] = [(filename, source, pid)]
            for folder, files in grouped_files.items():
                insert_records(db, folder, files)
            print()
            print("\033[1;32m# 已归档%s个文件。\033[0m" % (len(unsaved_files, )))
    else:
        print("# === 未发现未保存项 ===")


def __deduplicate(conf, db: Database, dry_run: bool):
    db_query_cache = dict()
    duplicated_files = []
    need_update_records = []

    all_folders = scan_folders(conf["work_path"]["archive_dir"])
    all_folders.sort(reverse=True)
    for folder in all_folders:
        # 扫描所有的folders，然后按照倒序，依次扫描每个folders下的项。
        # 这个扫描顺序能保证最小代价缓存，当db结果更大时，可以直接判定为重复项。
        matched_files, unmatched_files = scan_move_files(
            work_dir=os.path.join(conf["work_path"]["archive_dir"], folder),
            rules=conf["save"]["rules"],
            extensions=conf.get("supported_extensions")
        )

        for filename, source, pid, _ in matched_files:
            r = db_query_cache.get((source, pid), None)
            if r is None:
                # 还未建立缓存，表示当前查到的项是最新的那个项
                db_query_cache[(source, pid)] = (folder, filename)
                # 此时应该查询一次数据库，对已存储的值做个校验
                db_r = db.query_basic(source, pid)
                if db_r is not None:
                    db_folder, db_filename = db_r
                    if folder != db_folder:
                        # 此时，只要folder和记录值不对等，就认为是数据库记录需要更新了
                        need_update_records.append((folder, filename, db_folder, db_filename, source, pid))
            else:
                # 已经建立缓存，表示从现在开始，查询到的每一个项都是重复项了
                db_folder, db_filename = r
                duplicated_files.append((folder, filename, db_folder, db_filename))

    print()
    if len(duplicated_files) > 0:
        print("# === 发现重复项 %s项 ===" % (len(duplicated_files),))
        for folder, filename, db_folder, db_filename in duplicated_files:
            print("* \033[1;33m%-12s / %-30s\033[0m (Latest is %-12s/ %s)" % (folder, filename, db_folder, db_filename))
    else:
        print("# === 未发现重复项 ===")

    if len(need_update_records) > 0:
        print("# === 发现需要更新记录的项 %s项 ===" % (len(need_update_records),))
        for folder, filename, db_folder, db_filename, source, pid in need_update_records:
            print("* \033[1;33m%8s | %-12s |\033[0m FROM %-12s / %-30s TO %-12s / %-30s" % (source, pid, db_folder, db_filename, folder, filename))

    if not dry_run:
        print()
        if len(duplicated_files) > 0:
            do_delete_files(conf["work_path"]["archive_dir"], [(folder, filename) for folder, filename, _, _ in duplicated_files])
            print("\033[1;32m# 已清理%s个重复文件。\033[0m" % (len(duplicated_files, )))
        if len(need_update_records) > 0:
            grouped_files = dict()
            for folder, filename, _, _, source, pid in need_update_records:
                if folder in grouped_files:
                    grouped_files[folder].append((filename, source, pid))
                else:
                    grouped_files[folder] = [(filename, source, pid)]
            for folder, files in grouped_files.items():
                insert_records(db, folder, files)
            print("\033[1;32m# 已更新%s条过时记录。\033[0m" % (len(need_update_records, )))


def __mark_deleted(conf, db: Database, dry_run):
    deleted_records = []
    deleted_record_count = 0

    db_folders = db.query_folders()
    for db_folder in db_folders:
        db_filenames = db.query_folder_filenames(db_folder)
        not_existing_files = scan_not_existing_files(os.path.join(conf["work_path"]["archive_dir"], db_folder), db_filenames)
        if len(not_existing_files) > 0:
            deleted_records.append((db_folder, not_existing_files))
            deleted_record_count += len(not_existing_files)

    print()
    if deleted_record_count > 0:
        print("# === 发现已删除但未标记的记录 %s条 ===" % (deleted_record_count,))
        for (folder, files) in deleted_records:
            for file in files:
                print("* \033[1;33m%8s / %s\033[0m" % (folder, file))

        if not dry_run:
            for (folder, files) in deleted_records:
                for file in files:
                    db.mark_deleted(folder, file)
            print()
            print("\033[1;32m# 已标记%s条已删除记录。\033[0m" % (deleted_record_count, ))

    else:
        print("# === 未发已删除但未标记的记录 ===")
