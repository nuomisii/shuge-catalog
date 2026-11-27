import csv
from pathlib import Path
import tempfile
import unittest
from build_catalog import Entry, FIELDS, catalog_script, merge, read_source, safe_url


def active(node='a', item='001', rev=1, title='试题'):
    return Entry(node, item, rev, 'active', '试题', '示例课程', title, 'https://example.org/doc.pdf')


class CatalogTests(unittest.TestCase):
    def test_old_snapshot_does_not_revive_withdrawn(self):
        tombstone = Entry('a', '001', 2, 'withdrawn', '', '', '', '')
        self.assertEqual(merge([active()], [tombstone])[0], [])
        self.assertEqual(merge([tombstone], [active()])[0], [])
        self.assertEqual(merge([active(rev=3)], [tombstone])[0], [])

    def test_conflicts_and_stale_snapshot_do_not_publish(self):
        self.assertEqual(merge([active()], [active(title='另一版本')])[0], [])
        self.assertEqual(merge([active()], [active(rev=2)])[0], [])
        self.assertEqual(merge([active(rev=2)], [active()])[0], [active(rev=2)])

    def test_missing_nodes_and_rows_not_restored_from_history(self):
        self.assertEqual(merge([active()], [active(node='b'), active(item='002')])[0], [active()])

    def test_input_validation(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / '目录.csv'
            def write(*rows):
                with path.open('w', encoding='utf-8-sig', newline='') as f:
                    csv.writer(f).writerows([FIELDS, *rows])
            entry = ['a','001','1','active','试题','示例课程','试题','https://example.org/a.pdf']
            write(entry)
            self.assertEqual(list(read_source('a', path))[0].title, '试题')
            with self.assertRaisesRegex(ValueError, '不符'):
                list(read_source('another', path))
            write(entry, entry)
            with self.assertRaisesRegex(ValueError, '重复'):
                list(read_source('a', path))
            entry[6] = '=SUM(1,2)'
            write(entry)
            with self.assertRaises(ValueError):
                list(read_source('a', path))
            entry[6] = '<p>样本文字</p>'
            write(entry)
            with self.assertRaises(ValueError):
                list(read_source('a', path))

    def test_ui_nodes_follow_visible_rows_in_output_order(self):
        old = Entry('a-retired', '001', 2, 'withdrawn', '', '', '', '')
        visible, _ = merge([active(node='a-retired'), active(node='z', title='A'),
                            active(node='b', title='B')], [old])
        self.assertEqual(catalog_script(visible, '/* UI */'),
                         'const shugeRowNodes = ["z", "b"];\n/* UI */')

    def test_public_url_policy(self):
        self.assertTrue(safe_url('https://example.org/%E8%AF%95%E9%A2%98.pdf'))
        for url in ['http://example.org/a', 'https://user@example.org/a',
                    'https://example.org/a?key=123', 'https://example.org/#secret',
                    'javascript:alert(1)', 'https://example.org/<a>', 'https://hi\\host']:
            self.assertFalse(safe_url(url), url)


if __name__ == '__main__':
    unittest.main()
