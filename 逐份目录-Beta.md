# 逐份目录 · Beta

**试点范围：微积分 I-1，4 份已公开的期中试卷与解答。** 这里只试用按标题搜索、按课程、分类或来源节点筛选、逐份打开与导出 CSV；不代表全部课程已支持逐份下载。找其他资料请回[正式下载](README.md#正式下载)。

## 试用入口

- [查看已公开的试点目录 CSV](https://github.com/nuomisii/shuge-catalog/blob/pilot-calculus-i-1/catalog.csv)。四条下载链接随该 CSV 维护，此处不重复列出。
- 可搜索网页目前仅生成本地预览，不是在线服务。目录页面可以离线查看；打开 PDF 仍需联网。国内直连曾失败，尚未重新验收，打不开时可回到原有下载导航。

## 维护者：从 CSV 生成预览

先阅读[本地生成说明](tools/本地试用说明.md)，准备已核实的 `shuge-catalog` 节点当前快照和经校验的 csvtotable 3.2.0。替换两处占位路径，从仓库根目录运行；如已有撤回记录或已核实的旧快照，按说明传入 `--history`，不要用任意旧副本代替当前目录。

```powershell
$generator = 'C:\路径\csvtotable.exe'
$pilotCsv = 'C:\路径\catalog.csv'
New-Item -ItemType Directory -Force tools-output | Out-Null
python -X utf8 -B tools/build_catalog.py --csvtotable $generator `
  --source shuge-catalog $pilotCsv --out tools-output/微积分试点
```

打开 `tools-output/微积分试点/可搜索资料目录.html`。用本次试点快照应看到 4 条，搜索「解答」应剩 2 条。此快照只有一个来源节点；可用「清空筛选」恢复全部。输出目录已存在时换一个新名字；不要为生成预览而更改或发布源数据。预览随快照生成，旧副本不会自动更新。

## 反馈

按[参与说明](CONTRIBUTING.md)反馈条目编号、遇到的现象，以及是「目录打不开」还是「PDF 打不开」。试点暂停时可以单独撤下首页的 Beta 入口，不影响首批下载；移除入口不等于收回已下载的文件。
