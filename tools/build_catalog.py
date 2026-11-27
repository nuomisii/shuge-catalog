"""Build a reader catalog from explicitly approved, local UTF-8 snapshots."""
import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

FIELDS = 'node_id item_id revision status category course title url'.split()
READER_FIELDS = ('课程', '分类', '资料名称', '下载地址')
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z')


@dataclass(frozen=True)
class Entry:
    node: str
    item: str
    revision: int
    status: str
    category: str
    course: str
    title: str
    url: str

    @property
    def key(self):
        return self.node, self.item


def safe_text(text):
    return (text and text == text.strip() and text[0] not in '=+-@＝＋－＠'
            and not re.search(r'[<>\x00-\x1f\x7f]', text))


def safe_url(value):
    # V1 accepts plain, public HTTPS links only, not signed or tokenized URLs.
    if not re.fullmatch(r"[^\s<>\"'\\?#]+", value, re.ASCII) or not value.isascii():
        return False
    if any(ord(c) < 33 or ord(c) == 127 for c in value):
        return False
    try:
        url = urlsplit(value)
        _ = url.port
        return (url.scheme == 'https' and bool(url.hostname)
                and url.username is None and url.password is None)
    except ValueError:
        return False


def read_source(node, path):
    if not ID.fullmatch(node):
        raise ValueError(f'{path}: 无效的节点编号')
    seen = set()
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.reader(handle, strict=True)
        if next(reader, None) != FIELDS:
            raise ValueError(f'{path}: CSV 表头或列顺序不符')
        for row in reader:
            loc = f'{path}:{reader.line_num}'
            if len(row) != len(FIELDS):
                raise ValueError(f'{loc}: 应有 8 列')
            actual, item, rev, status, category, course, title, url = row
            if actual != node or not ID.fullmatch(item):
                raise ValueError(f'{loc}: 节点或条目编号不符')
            if item in seen:
                raise ValueError(f'{loc}: 同一快照内编号重复：{item}')
            seen.add(item)
            if not re.fullmatch(r'[1-9][0-9]{0,8}', rev):
                raise ValueError(f'{loc}: 版本须为 1 至 999999999 的整数')
            if status == 'active':
                if (category not in {'教辅资料', '试题'} or not safe_text(course)
                        or not safe_text(title) or not safe_url(url)):
                    raise ValueError(f'{loc}: 有效条目的分类、文本或公开 HTTPS 链接不符')
            elif status != 'withdrawn' or any((category, course, title, url)):
                raise ValueError(f'{loc}: 状态无效，或已撤回条目未清空公开字段')
            yield Entry(node, item, int(rev), status, category, course, title, url)


def merge(current, history):
    # Only verified current snapshots can supply a public row. History can only
    # veto it (withdrawal, newer known revision, or conflict). Missing is not withdrawal.
    versions = {}
    for row in [*current, *history]:
        versions.setdefault(row.key, set()).add(row)
    output, notices = [], []
    for candidate in current:
        rows = versions[candidate.key]
        label = '/'.join(candidate.key)
        if any(row.status == 'withdrawn' for row in rows):
            if candidate.status == 'active':
                notices.append((label, '存在撤回记录，未展示'))
            continue
        if any(row.revision > candidate.revision for row in rows):
            notices.append((label, '当前快照版本落后，未展示'))
        elif any(row.revision == candidate.revision and row != candidate for row in rows):
            notices.append((label, '同版本内容冲突，未展示'))
        else:
            output.append(candidate)
    return sorted(output, key=lambda e: (e.course, e.category, e.title, e.key)), sorted(notices)


def catalog_script(entries, ui):
    # The HTML source preserves CSV row order; DataTables passes its original
    # row index to fixed searches, even after sorting, filtering, or paging.
    # Only merged, visible entries supply the public node labels.
    nodes = json.dumps([entry.node for entry in entries]).replace('<', '\u003c')
    return f'const shugeRowNodes = {nodes};\n' + ui


def publish_preview(out, tool, entries):
    if out.exists():
        raise ValueError('输出目录已存在；请换新目录，避免覆盖或误读旧结果。')
    assets = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='.catalog-', dir=out.parent) as stage:
        target = Path(stage) / 'preview'
        target.mkdir()
        csv_path = target / '公开资料目录.csv'
        with csv_path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(READER_FIELDS)
            writer.writerows((e.course, e.category, e.title, e.url) for e in entries)
        # csvtotable consumes UTF-8 without BOM; the reader's CSV keeps its Excel-friendly BOM.
        source = Path(stage) / 'input.csv'
        source.write_text(csv_path.read_text(encoding='utf-8-sig'), encoding='utf-8', newline='')
        (target / '公开链接.txt').write_text(''.join(u + '\n' for u in sorted({e.url for e in entries})), encoding='utf-8')
        page = target / '可搜索资料目录.html'
        ui = Path(stage) / 'catalog_ui.js'
        ui.write_text(catalog_script(entries, (assets / 'catalog_ui.js').read_text(encoding='utf-8')),
                      encoding='utf-8')
        subprocess.run([str(tool), '--no-compress', '--theme', 'default', '--preserve-sort',
                        '--no-column-filters', '--export-options', 'csv', '--title', '书阁 2.0｜资料目录',
                        '--description', '可搜索资料，并按课程、分类或来源节点筛选。目录可离线查看，打开资料需要网络。',
                        '--css', str(assets / 'catalog.css'), '--js', str(ui),
                        str(source), str(page)], check=True)
        if not page.is_file():
            raise ValueError('生成器没有输出网页。')
        # Copy after a successful build rather than moving a directory whose
        # temporary Windows ACL may not be usable by the reader's browser.
        out.mkdir()
        names = ('公开资料目录.csv', '公开链接.txt', '可搜索资料目录.html')
        try:
            for name in names:  # Publish the entry page last.
                shutil.copyfile(target / name, out / name)
        except OSError:
            for name in names:
                (out / name).unlink(missing_ok=True)
            out.rmdir()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', nargs=2, action='append', required=True, metavar=('节点', 'CSV'))
    parser.add_argument('--history', nargs=2, action='append', default=[], metavar=('节点', 'CSV'))
    parser.add_argument('--csvtotable', type=Path, required=True, help='已验证的 csvtotable 3.2.0 可执行文件')
    parser.add_argument('--out', type=Path, required=True, help='尚不存在的预览目录；其上一级需已存在')
    args = parser.parse_args()
    try:
        nodes = [node for node, _ in args.source]
        if len(nodes) != len(set(nodes)):
            raise ValueError('每个节点只能指定一份当前快照；旧版本请用 --history。')
        current = [e for node, p in args.source for e in read_source(node, Path(p))]
        history = [e for node, p in args.history for e in read_source(node, Path(p))]
        entries, notices = merge(current, history)
        for label, notice in notices:
            print(f'{label}：{notice}', file=sys.stderr)
        if not entries:
            raise ValueError('没有可展示的条目，未生成预览；请核对输入和撤回记录。')
        tool = args.csvtotable.resolve(strict=True)
        version = subprocess.run([str(tool), '--version'], check=True, capture_output=True, text=True)
        if version.stdout.strip().split()[-1:] != ['3.2.0']:
            raise ValueError('本界面只验证过 csvtotable 3.2.0。')
        publish_preview(args.out.resolve(), tool, entries)
        print(f'已生成 {len(entries)} 条资料：{args.out.resolve()}')
    except (OSError, ValueError, csv.Error, subprocess.SubprocessError) as error:
        parser.exit(1, f'生成失败：{error}\n')


if __name__ == '__main__':
    main()
