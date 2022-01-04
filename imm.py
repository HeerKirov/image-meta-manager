import click
import command


@click.group(help="IMM: 图像元数据管理器")
def imm():
    pass


@imm.command("rename", help="整理重命名图像文档")
@click.option("--work-dir", "-d", help="显式指定工作目录")
@click.option("--dry-run", is_flag=True, help="模拟重命名结果并打印，并不实际执行重命名操作")
@click.option("--verbose", "-v", is_flag=True, help="打印详细的重命名计划列表")
def rename(work_dir, dry_run, verbose):
    command.rename(work_dir, dry_run, verbose)


@imm.command("save", help="移动，并将图像信息保存入库")
@click.option("--work-dir", "-d", help="显式指定工作目录")
@click.option("--archive", "-a", help="显示指定保存目录。不指定的情况下，默认根据今天的日期生成目录")
@click.option("--split", "-s", help="指定一个分割的存档。指定后，会使用类似yyyy-MM-dd.N的存档文件夹")
@click.option("--replace", "-r", is_flag=True, help="对于库中已有的重复文件，执行替换操作")
@click.option("--no-meta", "-n", is_flag=True, help="对于无元数据匹配的项，同样允许存档，但不保存元数据")
@click.option("--dry-run", is_flag=True, help="模拟保存结果并打印，并不实际执行保存和移动操作")
def save(work_dir, archive, split, replace, no_meta, dry_run):
    command.save(work_dir, archive, split, replace, no_meta, dry_run)


@imm.command("download", help="下载图像的元数据")
def download():
    command.download()


@imm.command("organize", help="根据选项，整理文件和数据库")
@click.option("--deduplicate", "-d", is_flag=True, help="移除文件库中的重复文件，以最后一次存档为准，并移除稍早的重复文件")
@click.option("--unsaved", "-s", is_flag=True, help="查找文件库中的未保存文件，并加入保存")
@click.option("--mark-deleted", "-m", is_flag=True, help="搜索并在数据库中标记已被删除的文件，添加已删除标记")
@click.option("--dry-run", is_flag=True, help="模拟整理结果并打印，并不实际执行整理操作")
def organize(deduplicate, unsaved, mark_deleted, dry_run):
    command.organize(deduplicate, unsaved, mark_deleted, dry_run)


@imm.command("export", help="导出元数据")
@click.option("--archive", "-a", help="指定保存目录")
@click.option("--source", "-s", help="指定来源类型")
@click.option("--output", "-o", help="指定输出文件")
def export(archive, source, output):
    command.export(archive, source, output)


@imm.group(help="查询元数据库")
def query():
    pass


@query.command(name="one", help="查询一条指定的图像元数据")
@click.argument("source")
@click.argument("pid")
@click.option("--all", "-a", is_flag=True, help="展示全部数据，而非仅简要数据")
@click.option("--show", "-s", is_flag=True, help="同时在文件管理器展示此文件")
@click.option("--open", "-o", is_flag=True, help="同时打开此文件")
def query_one(source, pid, all, show, open):
    print("query one")


@query.command(name="list", help="查询符合条件的数据记录列表")
@click.option("--source", "-s", help="过滤指定的数据源类型")
@click.option("--create-from", "-c", help="过滤某个时间点之后的数据")
@click.option("--limit", "-l", help="限制查询数量", default=20)
def query_list(source, create_from, limit):
    print("query list")


if __name__ == '__main__':
    imm()
