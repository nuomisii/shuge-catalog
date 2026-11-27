(() => {
  'use strict';
  document.documentElement.lang = 'zh-CN';
  const table = CsvToTable.table;
  const host = table.table().container();
  const search = host.querySelector('.dt-search input');
  search.placeholder = '搜索资料，如「解答」';
  search.setAttribute('aria-label', search.placeholder);
  const filters = document.createElement('div');
  filters.className = 'shuge-filters';
  host.querySelector('.dt-layout-row').after(filters);
  const selects = [];
  for (const [index, label] of [[0, '课程'], [1, '分类']]) {
    const wrap = document.createElement('label');
    const select = document.createElement('select');
    select.id = `shuge-filter-${index}`;
    select.add(new Option('全部', ''));
    for (const value of [...new Set(table.column(index).data().toArray())].sort((a,b) => a.localeCompare(b, 'zh-CN'))) {
      select.add(new Option(value, value));
    }
    selects.push(select);
    wrap.append(`${label}：`, select);
    filters.append(wrap);
    select.addEventListener('change', () => table.column(index).search(select.value, {exact: Boolean(select.value)}).draw());
  }
  const source = document.createElement('select');
  source.id = 'shuge-filter-source';
  source.add(new Option('全部', ''));
  for (const node of [...new Set(shugeRowNodes)].sort()) source.add(new Option(node, node));
  const sourceLabel = document.createElement('label');
  sourceLabel.append('来源节点：', source);
  filters.append(sourceLabel);
  source.addEventListener('change', () => {
    const node = source.value;
    table.search.fixed('shuge-source', node ? (_text, _row, index) => shugeRowNodes[index] === node : null).draw();
  });
  const reset = document.createElement('button');
  reset.type = 'button';
  reset.textContent = '清空筛选';
  reset.addEventListener('click', () => {
    search.value = '';
    for (const select of [...selects, source]) select.value = '';
    table.search('');
    for (const index of [0, 1]) table.column(index).search('', {exact: false});
    table.search.fixed('shuge-source', null).draw();
  });
  filters.append(reset);
  const csvButton = host.querySelector('.buttons-csv span');
  csvButton.textContent = '导出 CSV';
  csvButton.closest('button').removeAttribute('aria-label');
  function refresh() {
    const empty = host.querySelector('.dt-empty');
    if (empty) empty.textContent = '没有符合条件的资料';
    const info = host.querySelector('.dt-info');
    if (info) info.textContent = `显示 ${table.rows({search:'applied'}).count()} / ${table.rows().count()} 份资料`;
    table.rows({page:'current'}).every(function () {
      const row = this.node();
      const [,,title, address] = this.data();
      const url = new URL(address);
      if (!url || url.protocol !== 'https:' || url.username || url.password) {
        row.cells[3].textContent = '链接不可用';
        return;
      }
      const a = document.createElement('a');
      a.href = url.href;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.textContent = '打开资料';
      a.setAttribute('aria-label', `打开资料：${title}`);
      row.cells[3].replaceChildren(a);
    });
  }
  table.on('draw', refresh);
  refresh();
})();
