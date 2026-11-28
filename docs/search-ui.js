(() => {
  'use strict';
  const rows = window.shugeSearchIndex;
  if (!Array.isArray(rows)) return;
  const box = document.querySelector('#catalog-search');
  const query = box.querySelector('#search-query');
  const filter = box.querySelector('#search-kind');
  const list = box.querySelector('#search-results');
  const status = box.querySelector('#search-status');
  const pager = box.querySelector('#search-pagination');
  const prev = box.querySelector('#search-prev');
  const next = box.querySelector('#search-next');
  const pageLabel = box.querySelector('#search-page');
  const clear = box.querySelector('#search-clear');
  const normalize = value => value.normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
  const indexed = rows.map(([title, course, group, batch, kind, page, download]) => ({
    title, course, group, batch, kind, page, download,
    titleKey: normalize(title), courseKey: normalize(course),
    keys: [title, course, group, batch, kind, download ? decodeURIComponent(download.split('/').pop()) : ''].map(normalize),
  }));
  const home = new URL('./index.html', window.location.href);
  const limit = 25;
  let matches = [], current = 1, composing = false;

  const node = (tag, text) => Object.assign(document.createElement(tag), {textContent: text});
  function link(text, href) {
    const a = node('a', text);
    a.href = href;
    return a;
  }
  function renderPage(moveFocus = false) {
    const total = Math.ceil(matches.length / limit);
    const from = (current - 1) * limit;
    const end = Math.min(from + limit, matches.length);
    list.replaceChildren();
    list.start = from + 1;
    for (const row of matches.slice(from, end)) {
      const item = node('li', '');
      const page = new URL(row.page, home);
      item.append(link(row.title, row.download || page));
      const context = node('small', [...new Set([row.batch, row.kind, row.course, row.group].filter(Boolean))].join(' · '));
      if (row.download) context.append(' · ', link('查看目录', page));
      item.append(context);
      list.append(item);
    }
    status.textContent = total ? `找到 ${matches.length} 条，显示第 ${from + 1}–${end} 条。` : '没有找到匹配资料。试试更短的关键词，或切换到「全部类型」。';
    pager.hidden = total <= 1;
    pageLabel.textContent = total ? `第 ${current} / ${total} 页` : '';
    prev.disabled = current <= 1;
    next.disabled = current >= total;
    if (moveFocus) list.querySelector('a')?.focus();
  }
  function turn(delta) {
    const target = current + delta;
    if (target < 1 || target > Math.ceil(matches.length / limit)) return;
    current = target;
    renderPage(true);
  }
  function update() {
    const words = query.value.trim().split(/\s+/u).map(normalize).filter(Boolean);
    const kind = filter.value;
    list.replaceChildren();
    current = 1;
    if (!words.length && !kind) {
      status.textContent = query.value.trim() ? '请输入课程名、文件名或年份。' : '';
      matches = [];
      pager.hidden = true;
      return;
    }
    const joined = words.join('');
    const score = row => !joined ? 0 : (row.titleKey === joined ? 100 : row.titleKey.startsWith(joined) ? 30 : 0) + (row.courseKey === joined ? 20 : 0) + words.filter(word => row.titleKey.includes(word)).length;
    matches = indexed.filter(row => (!kind || row.kind === kind) && words.every(word => row.keys.some(key => key.includes(word))))
      .sort((a,b) => score(b) - score(a));
    renderPage();
  }
  box.addEventListener('submit', event => {event.preventDefault(); if (!composing) update();});
  query.addEventListener('compositionstart', () => {composing = true;});
  query.addEventListener('compositionend', () => {composing = false; update();});
  query.addEventListener('input', () => {if (!composing) update();});
  filter.addEventListener('change', update);
  prev.addEventListener('click', () => turn(-1));
  next.addEventListener('click', () => turn(1));
  clear.addEventListener('click', () => {box.reset(); update(); query.focus();});
  box.hidden = false;
  update();
})();
