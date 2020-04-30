# image meta manager
A little tool to manage image meta.

## command line interface
```bash
imm scan refer         # 扫描符合匹配条件的文件夹下的文件，并根据来源推断正确命名
    [DIR PATTERN]           # 文件夹名称匹配的正则表达式
    -a|-all                 # 显示所有扫描结果，而不仅仅是需要重命名的文件
    -r|-rename              # 按照推断重命名所有文件
imm scan file            # 扫描符合匹配条件的文件夹下的文件
    [DIR PATTERN]           # 文件夹名称匹配的正则表达式
    -save                   # 将扫描结果保存到数据库
    --duplicate             # 对重复扫描的策略[warn|ignore|replace]，默认是warn
imm scan dir            # 扫描根目录下符合条件的文件夹名称
    [DIR PATTERN]           # 文件夹名称匹配的正则表达式
imm query one           # 精确查询指定的记录
    [SOURCE]                # 数据来源站
    [PID]                   # 图像ID
    -a|-all                 # 列出详细而不是简略的元数据
    -d|-download            # 更新此记录的元数据
imm query list          # 在数据库中查找一批记录
    --filename [FILE]       # 按记录文件名匹配过滤
    --source [SOURCE]       # 按来源查找
    --create-from [DATE]    # 查找指定创建时间以来的记录
    --analyse-from [DATE]   # 查找指定分析时间以来的记录
    --status [STATUS]       # 查找指定记录状态的记录，可以使用列表组合
    --order [ORDER]         # 排序方式，默认按插入排序，可选create-time, analyse-time, status, source, pid, filepath，可组合，加负号表反向排序
    --limit [LIMIT]         # 限制本次查找的记录数
    -d|-download            # 更新所有记录的元数据
    -i|--interval [INTERVAL]# 更新数据的缓冲间隔时间(s)
```

## TODO
* 编写konachan module
* 编写pixiv module