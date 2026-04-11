import { useState, useEffect, useRef, useCallback } from 'react';
import { Modal, message, Spin } from 'antd';
import { getMarketNPCs, exportNPCs, importNPCs } from '@/api/god';
import type { MarketNPCData, NPCExportData } from '@/api/types';
import { calcStats } from './MarketStats';
import { NPCMarketCard } from './NPCMarketCard';
import { NPCMarketDetail } from './NPCMarketDetail';
import './NPCMarket.css';
import { useT } from '@/i18n';

type Filter = 'all' | 'online' | 'skilled' | 'wechat';
type SortKey = 'overall' | 'skillLevel' | 'memory' | 'name';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function NPCMarket({ open, onClose }: Props) {
  const t = useT();
  const [npcs, setNpcs] = useState<MarketNPCData[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<Filter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('overall');
  const [detailNpc, setDetailNpc] = useState<MarketNPCData | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await getMarketNPCs();
      if (data.status === 'ok') setNpcs(data.npcs);
    } catch { message.error(t('market.loadFailed')); }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (open) loadData();
  }, [open, loadData]);

  // 筛选
  const filtered = npcs.filter(npc => {
    if (filter === 'online') return npc.enabled;
    if (filter === 'skilled') return npc.skills.length > 0;
    if (filter === 'wechat') return npc.wechat_status === 'bound';
    return true;
  });

  // 排序
  const sorted = [...filtered].sort((a, b) => {
    if (sortKey === 'name') return a.name.localeCompare(b.name);
    const sa = calcStats(a);
    const sb = calcStats(b);
    return sb[sortKey] - sa[sortKey];
  });

  // 导出单个
  const handleExport = async (name: string) => {
    try {
      const { data } = await exportNPCs([name]);
      if (data.status === 'ok' && data.npcs) {
        const blob = new Blob([JSON.stringify(data.npcs, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${name}.json`;
        a.click();
        URL.revokeObjectURL(url);
        message.success(`${t('market.exported')} ${name}`);
      }
    } catch { message.error(t('common.exportFailed')); }
  };

  // 全部导出
  const handleExportAll = async () => {
    const names = npcs.map(n => n.name);
    if (names.length === 0) return;
    try {
      const { data } = await exportNPCs(names);
      if (data.status === 'ok' && data.npcs) {
        const blob = new Blob([JSON.stringify(data.npcs, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const d = new Date().toISOString().slice(0, 10);
        a.download = `npc_market_${d}.json`;
        a.click();
        URL.revokeObjectURL(url);
        message.success(`${t('market.exported')} ${data.npcs.length} ${t('market.countNPC')}`);
      }
    } catch { message.error(t('common.exportFailed')); }
  };

  // 导入
  const handleImportFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        let parsed = JSON.parse(ev.target?.result as string);
        // 兼容 { npcs: [...] } 和 [...] 两种格式
        const importData: NPCExportData[] = Array.isArray(parsed) ? parsed : (parsed.npcs || []);
        if (importData.length === 0) {
          message.warning(t('market.noNPCData'));
          return;
        }
        const { data } = await importNPCs(importData, false);
        if (data.status === 'ok') {
          message.success(`${t('market.importSuccess')} ${data.imported_count} ${t('market.countNPC')}`);
          loadData();
        } else {
          message.error(data.message || t('common.importFailed'));
        }
      } catch { message.error(t('market.fileParseFailed')); }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const onlineCount = npcs.filter(n => n.enabled).length;

  const FILTERS: { key: Filter; label: string }[] = [
    { key: 'all', label: t('market.filterAll') },
    { key: 'online', label: t('market.filterOnline') },
    { key: 'skilled', label: t('market.filterSkilled') },
    { key: 'wechat', label: t('market.filterWechat') },
  ];

  const SORTS: { key: SortKey; label: string }[] = [
    { key: 'overall', label: t('market.sortOverall') },
    { key: 'skillLevel', label: t('market.sortSkill') },
    { key: 'memory', label: t('market.sortMemory') },
    { key: 'name', label: t('market.sortName') },
  ];

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width="95vw"
      styles={{
        body: {
          background: '#0f172a',
          padding: 0,
          height: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        },
        content: { background: '#0f172a', borderRadius: 8 },
      }}
      centered
      destroyOnClose
    >
      {/* 标题栏 */}
      <div style={{
        textAlign: 'center',
        padding: '14px 0 10px',
        borderBottom: '2px solid #334155',
        background: 'linear-gradient(180deg, #1e293b 0%, #0f172a 100%)',
      }}>
        <div style={{
          fontSize: 20,
          fontWeight: 700,
          color: '#e2e8f0',
          letterSpacing: 4,
          textShadow: '0 0 8px #38bdf830',
        }}>
          {t('market.title')}
        </div>
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
          {t('market.subtitle')}
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="market-filter-bar">
        {FILTERS.map(f => (
          <button
            key={f.key}
            className={`market-filter-btn ${filter === f.key ? 'market-filter-btn--active' : ''}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 10, color: '#64748b', marginRight: 4 }}>{t('market.sortLabel')}</span>
        {SORTS.map(s => (
          <button
            key={s.key}
            className={`market-filter-btn ${sortKey === s.key ? 'market-filter-btn--active' : ''}`}
            onClick={() => setSortKey(s.key)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* 网格区 */}
      <div style={{ flex: 1, overflow: 'auto', padding: '4px 0' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin /></div>
        ) : (
          <div className="market-grid">
            {sorted.map(npc => (
              <NPCMarketCard
                key={npc.name}
                npc={npc}
                onDetail={setDetailNpc}
                onExport={handleExport}
              />
            ))}

            {/* 导入卡片 */}
            <div className="market-card--import" onClick={() => fileInputRef.current?.click()}>
              <div className="import-icon">+</div>
              <div>{t('market.importCard')}</div>
              <div style={{ fontSize: 10, marginTop: 4, color: '#475569' }}>{t('market.importHint')}</div>
            </div>
          </div>
        )}
      </div>

      {/* 底栏 */}
      <div className="market-footer">
        <span>
          {t('market.total')} {npcs.length} {t('market.countNPC')} · {onlineCount} {t('market.online')}
        </span>
        <div className="market-footer-actions">
          <button className="market-filter-btn" onClick={() => fileInputRef.current?.click()}>
            {t('market.importFile')}
          </button>
          <button className="market-filter-btn" onClick={handleExportAll}>
            {t('market.exportAll')}
          </button>
        </div>
      </div>

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        style={{ display: 'none' }}
        onChange={handleImportFile}
      />

      {/* 详情面板 */}
      <NPCMarketDetail
        npc={detailNpc}
        open={!!detailNpc}
        onClose={() => setDetailNpc(null)}
        onExport={handleExport}
      />
    </Modal>
  );
}
