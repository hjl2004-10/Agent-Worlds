/**
 * DocsPage - 大厂风格文档站 (全屏页, 哈希路由 #/docs[/<pageId>] 进入)
 */

import { useEffect, useMemo, useState } from 'react';
import { Input, Button, Tag, Tooltip } from 'antd';
import {
  SearchOutlined,
  ArrowLeftOutlined,
  GithubOutlined,
  SunOutlined,
  MoonOutlined,
  BookOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useLocaleStore } from '@/store/useLocaleStore';
import { useThemeStore } from '@/store/useThemeStore';
import { zhGroups } from './content.zh';
import { enGroups } from './content.en';
import './docs.css';

function parseHash(): { open: boolean; pageId: string } {
  const h = window.location.hash || '';
  if (!h.startsWith('#/docs')) return { open: false, pageId: '' };
  const rest = h.slice('#/docs'.length).replace(/^\//, '');
  return { open: true, pageId: decodeURIComponent(rest) };
}

export function navigateToDocs(pageId?: string) {
  window.location.hash = pageId ? `#/docs/${encodeURIComponent(pageId)}` : '#/docs';
}

export function DocsPage() {
  const { locale } = useLocaleStore();
  const { theme, toggle: toggleTheme } = useThemeStore();
  const isZh = locale === 'zh';
  const groups = isZh ? zhGroups : enGroups;

  const [pageId, setPageId] = useState(() => parseHash().pageId || 'quickstart');
  const [query, setQuery] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // 哈希变化 -> 切页 (支持浏览器前进后退 / 外链直达)
  useEffect(() => {
    const onHash = () => {
      const { open, pageId: pid } = parseHash();
      if (open && pid) setPageId(pid);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const flat = useMemo(
    () => groups.flatMap(g => g.pages.map(p => ({ ...p, group: g.label }))),
    [groups],
  );

  const currentPage = flat.find(p => p.id === pageId) || flat[0];

  const filteredGroups = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups;
    return groups
      .map(g => ({
        ...g,
        pages: g.pages.filter(
          p => p.title.toLowerCase().includes(q) || p.md.toLowerCase().includes(q),
        ),
      }))
      .filter(g => g.pages.length > 0);
  }, [groups, query]);

  const goPage = (id: string) => {
    setPageId(id);
    navigateToDocs(id);
    document.querySelector('.docs-content-scroll')?.scrollTo({ top: 0 });
  };

  const idx = flat.findIndex(p => p.id === currentPage.id);
  const prev = idx > 0 ? flat[idx - 1] : null;
  const next = idx >= 0 && idx < flat.length - 1 ? flat[idx + 1] : null;

  return (
    <div className="docs-root">
      {/* 顶栏 */}
      <header className="docs-header">
        <div className="docs-header-left">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => { window.location.hash = ''; }}
            className="docs-back"
          >
            {isZh ? '返回应用' : 'Back to App'}
          </Button>
          <span className="docs-brand">
            <BookOutlined /> Agent-Worlds <span className="docs-brand-docs">Docs</span>
          </span>
        </div>
        <div className="docs-header-right">
          <Input
            allowClear
            prefix={<SearchOutlined style={{ opacity: 0.5 }} />}
            placeholder={isZh ? '搜索文档…' : 'Search docs…'}
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="docs-search"
          />
          <Tooltip title={theme === 'dark' ? (isZh ? '切换亮色' : 'Light') : (isZh ? '切换暗色' : 'Dark')}>
            <Button
              type="text"
              icon={theme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
            />
          </Tooltip>
          <Tooltip title="GitHub">
            <Button
              type="text"
              icon={<GithubOutlined />}
              href="https://github.com/hjl2004-10/Agent-Worlds"
              target="_blank"
            />
          </Tooltip>
        </div>
      </header>

      <div className="docs-body">
        {/* 侧边栏 */}
        <aside className={`docs-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
          <div className="docs-sidebar-toggle" onClick={() => setSidebarCollapsed(v => !v)}>
            {sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </div>
          {!sidebarCollapsed && (
            <nav>
              {filteredGroups.map(g => (
                <div key={g.label} className="docs-group">
                  <div className="docs-group-label">{g.label}</div>
                  {g.pages.map(p => (
                    <div
                      key={p.id}
                      className={`docs-nav-item ${p.id === currentPage.id ? 'active' : ''}`}
                      onClick={() => goPage(p.id)}
                    >
                      {p.title}
                    </div>
                  ))}
                </div>
              ))}
              {filteredGroups.length === 0 && (
                <div className="docs-empty">{isZh ? '无匹配结果' : 'No results'}</div>
              )}
            </nav>
          )}
        </aside>

        {/* 内容区 */}
        <main className="docs-content-scroll">
          <article className="docs-article">
            <div className="docs-article-tag">
              <Tag color="green">{currentPage.group}</Tag>
            </div>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{currentPage.md}</ReactMarkdown>

            <div className="docs-pager">
              {prev ? (
                <div className="docs-pager-btn" onClick={() => goPage(prev.id)}>
                  <span className="docs-pager-dir">← {isZh ? '上一篇' : 'Prev'}</span>
                  <span className="docs-pager-title">{prev.title}</span>
                </div>
              ) : <span />}
              {next ? (
                <div className="docs-pager-btn right" onClick={() => goPage(next.id)}>
                  <span className="docs-pager-dir">{isZh ? '下一篇' : 'Next'} →</span>
                  <span className="docs-pager-title">{next.title}</span>
                </div>
              ) : <span />}
            </div>
          </article>
        </main>
      </div>
    </div>
  );
}

/** 根级哈希路由: #/docs 开头则渲染文档站, 否则渲染主应用 */
export function isDocsHash() {
  return parseHash().open;
}
