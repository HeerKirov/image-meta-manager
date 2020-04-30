from util.parameters import parameters, Command
from .scan import scan_file, scan_dir, scan_refer
from .query import query_list, query_one
from .cli import cli


root_command = Command(comment='管理维护本地的Image资料库和元数据库').next(
    Command('scan', comment='对本地硬盘上的资料库进行扫描')
    .next(
        Command('refer', comment='扫描符合匹配条件的文件夹下的文件，并根据来源推断正确命名')
        .a('dir', display_name='DIR_PATTERN', required=True, comment='文件夹名称匹配的正则表达式')
        .f('all', display_list=['a', 'all'], comment='显示所有扫描结果，而不仅仅是需要重命名的文件')
        .f('rename', display_list=['r', 'rename'], comment='按照推断重命名所有文件')
        .do(scan_refer),

        Command('file', comment='扫描符合匹配条件的文件夹下的文件')
        .a('dir', display_name='DIR_PATTERN', required=True, comment='文件夹名称匹配的正则表达式')
        .f('save', display_list=['save', 's'], comment='将扫描结果保存到数据库')
        .p('duplicate', clazz=['warn', 'ignore', 'replace'], default='warn',
           comment='对重复存储的策略[warn|ignore|replace]，默认是warn')
        .do(scan_file),

        Command('dir', comment='扫描根目录下符合条件的文件夹名称')
        .a('dir', display_name='DIR_PATTERN', required=True, comment='文件夹名称匹配的正则表达式')
        .do(scan_dir)
    ),
    Command('query', comment='查询数据库中的记录').next(
        Command('one', comment='精确查询数据库指定的记录')
        .a('source', display_name='SOURCE', required=True, comment='数据来源分类')
        .a('pid', display_name='PID', required=True, comment='图像ID')
        .f('all', display_list=['a', 'all'], comment='列出详细而不是简略的元数据')
        .f('download', display_list=['d', 'download'], comment='更新此记录的元数据')
        .do(query_one),

        Command('list', comment='按过滤条件在数据库中查找一批记录')
        .p('folder', display_name='FOLDER', comment='按记录文件夹匹配过滤')
        .p('filename', display_name='FILE', comment='按记录文件名匹配过滤')
        .p('source', display_name='SOURCE', clazz=(list, str), comment='按来源查找，可组合')
        .p('create-from', display_name='DATE', comment='查找指定创建时间以来的记录')
        .p('analyse-from', display_name='DATE', comment='查找指定分析时间以来的记录')
        .p('status', display_name='STATUS', clazz=(list, ['not-analysed', 'analysed', 'error']),
           comment='查找指定记录状态的记录，包括[not_analysed, analysed, error]，可组合')
        .p('order', display_name='ORDER',
           clazz=(list, ['create-time', 'analyse-time', 'status', 'source', 'pid', 'folder', 'filename',
                         '-create-time', '-analyse-time', '-status', '-source', '-pid', '-folder', '-filename']),
           comment='排序方式，默认按插入排序，可选create-time, analyse-time, status, source, pid, filepath，可组合，加负号表反向排序')
        .p('limit', display_name='LIMIT', clazz=int, comment='限制本次查找的记录数')
        .f('download', display_list=['d', 'download'], comment='更新所有记录的元数据')
        .p('interval', display_list=['interval', 'i'], clazz=float, default=0, comment='更新数据时的缓冲间隔时间')
        .do(query_list),
    ),
    Command('cli', comment='进入交互命令行模式')
    .do(cli)
)


def run_command_arguments(arguments):
    root_command.execute(**parameters(arguments))


def run_command_argv(argv):
    if not root_command.execute(**parameters(argv)):
        exit(1)
