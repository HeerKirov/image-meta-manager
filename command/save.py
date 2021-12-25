from module.local import scan_move_files, do_move_files, do_delete_files, get_today_archive
from module.database import Database, scan_record_existence, insert_records
from module.config import load_conf
import os


def save(work_dir, archive, split, replace, no_meta, dry_run):
    """
    将工作目录下的文件移动到存档目录的指定位置，同时根据分析规则，将文件的来源信息保存到数据库。
    扫描文件仅在工作目录下进行，并且仅扫描supported_extensions中指定的扩展名。如果没有指定此配置，那么会扫描所有文件。
    完成基本扫描之后，根据rules规则进行匹配。匹配成功后，将文件移入归档并保存来源。
    移入的归档目录会根据今天的日期生成，并位于archive_dir目录下，默认格式yyyy-MM-dd。使用offset配置项可以偏移日期计算，使用split选项可以增加分割点。
    如果不能完成任何匹配，默认是不接受移入无元数据的项的，会拒绝移入。使用no-meta选项，指示强制存储无元数据的文件，这将仅移入而不存储其元数据。
    如果文件在数据库中已存在其他相同来源项，默认也不接受重复文件存入，同样拒绝移入。使用replace选项，指示强制替代旧的文件，这也将自动移除旧文件。

    :param work_dir: 显式指定工作目录，而不是使用默认路径。如果没有配置默认工作目录，则使用当前目录
    :param split: 指定一个分割的存档。指定后，会使用类似yyyy-MM-dd.N的存档文件夹。这可以帮助分割存放
    :param archive: 显示指定存档文件夹的位置。如果不指定，则根据今天的日期生成目录。使用此参数后split参数无效
    :param no_meta: 指示在无元数据时，仅移入而不存储元数据
    :param replace: 指示在重复文件时，选择替代旧文件存入，并替代旧文件
    :param dry_run: 试运行，生成并打印执行计划，但不实际执行计划
    """
    conf = load_conf()
    work_dir = work_dir or conf["work_path"]["default_work_dir"]
    archive_dir_name = get_today_archive(conf["save"].get("archive_time_offset"), split)
    archive_target_dir = archive or os.path.join(conf["work_path"]["archive_dir"], archive_dir_name)

    matched_files, unmatched_files = scan_move_files(
        work_dir=work_dir,
        rules=conf["save"]["rules"],
        extensions=conf.get("supported_extensions"),
    )

    db = Database(conf["work_path"]["db_path"])

    move_files, exist_files = scan_record_existence(db, matched_files)

    print("# 扫描总数: %s, 移动并归档: %s, 未匹配: %s, 已存在: %s" % (len(matched_files) + len(unmatched_files), len(move_files), len(unmatched_files), len(exist_files)))
    print("# 归档目标文件夹: \033[1;34m%s\033[0m" % (archive_dir_name,))

    if len(unmatched_files) > 0:
        print()
        print("# === 发现未匹配文件 %s项 ===" % (len(unmatched_files),))
        for item in unmatched_files:
            print("* \033[1;31m%s\033[0m" % (item,))

    if len(exist_files) > 0:
        print()
        print("# === 发现已存在文件 %s项 ===" % (len(exist_files),))
        filename_max_length = max([len(o) for (o, _, _, _, _) in exist_files])
        for (filename, source, pid, exist_archive, exist_filename) in exist_files:
            print(("* \033[1;33m%-" + str(filename_max_length) + "s\033[0m : \033[1;33m%s/%s\033[0m") % (filename, exist_archive, exist_filename))

    print()

    if not dry_run:
        if len(move_files) > 0:
            insert_records(db, archive_dir_name, move_files)
            do_move_files(work_dir, archive_target_dir, [filename for (filename, _, _) in move_files])
            print("\033[1;32m# 已移动并归档%s个文件。\033[0m" % (len(move_files,)))
        if len(unmatched_files) > 0 and no_meta:
            do_move_files(work_dir, archive_target_dir, unmatched_files)
            print("\033[1;32m# 由于已指定允许无元数据归档，已移动%s个未匹配的文件。\033[0m" % (len(unmatched_files,)))
            pass
        if len(exist_files) > 0 and replace:
            do_move_files(work_dir, archive_target_dir, [filename for (filename, _, _, _, _) in exist_files])
            do_delete_files(conf["work_path"]["archive_dir"], [(folder, filename) for (_, _, _, folder, filename) in exist_files])
            insert_records(db, archive_dir_name, [(filename, source, pid) for (filename, source, pid, _, _) in exist_files])
            print("\033[1;32m# 由于已指定允许替代，已移动并归档%s个重复存在的文件，且已删除它们的旧文件。\033[0m" % (len(exist_files, )))
            pass

    if len(unmatched_files) > 0 and not no_meta:
        print("\033[1;31m# 存在无法处理的未匹配文件。无法解析其元信息，请重命名、指定无元数据归档、或手动完成处理。\033[0m")

    if len(exist_files) > 0 and not replace:
        print("\033[1;33m# 存在元信息重复存在的文件。请对比新旧文件，然后移除新文件以使用旧文件、或使用替代选项以替代旧文件。\033[0m")
