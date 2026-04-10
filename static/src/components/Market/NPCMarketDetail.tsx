import { useState, useEffect } from 'react';
import { Drawer, Tag, Divider, Space } from 'antd';
import { calcStats, getRank, STAT_DEFS } from './MarketStats';
import { getSkillDetail, getAvailableTools } from '@/api/god';
import type { MarketNPCData, SkillDetail } from '@/api/types';

const AVATARS = [
  '/ui/avatars/soldier.png', '/ui/avatars/hacker.png',
  '/ui/avatars/merchant.png', '/ui/avatars/scientist.png',
  '/ui/avatars/medic.png', '/ui/avatars/officer.png',
  '/ui/avatars/chef.png', '/ui/avatars/robot.png',
  '/ui/avatars/assassin.png', '/ui/avatars/brawler.png',
  '/ui/avatars/mechanic.png', '/ui/avatars/sniper.png',
];

function getAvatar(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATARS[Math.abs(hash) % AVATARS.length];
}

// 展开详情块的内联样式
const expandStyle: React.CSSProperties = {
  marginTop: 6,
  padding: '8px 10px',
  background: '#1e293b',
  borderRadius: 6,
  fontSize: 11,
  lineHeight: 1.6,
  color: '#94a3b8',
  borderLeft: '2px solid #6366f1',
};

interface Props {
  npc: MarketNPCData | null;
  open: boolean;
  onClose: () => void;
  onExport: (name: string) => void;
}

export function NPCMarketDetail({ npc, open, onClose, onExport }: Props) {
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);
  const [skillCache, setSkillCache] = useState<Record<string, SkillDetail>>({});
  const [expandedTool, setExpandedTool] = useState<string | null>(null);
  const [toolMap, setToolMap] = useState<Record<string, string>>({});

  // 切换 NPC 时重置展开状态
  useEffect(() => {
    setExpandedSkill(null);
    setExpandedTool(null);
  }, [npc?.name]);

  // 一次性加载工具描述
  useEffect(() => {
    if (!open) return;
    getAvailableTools().then(({ data }) => {
      if (data.status === 'ok') {
        const map: Record<string, string> = {};
        data.tools.forEach(t => { map[t.id] = t.description; });
        setToolMap(map);
      }
    }).catch(() => {});
  }, [open]);

  if (!npc) return null;

  const stats = calcStats(npc);
  const rank = getRank(stats.overall);

  // 点击技能标签
  const handleSkillClick = async (name: string) => {
    if (expandedSkill === name) { setExpandedSkill(null); return; }
    if (!skillCache[name]) {
      try {
        const { data } = await getSkillDetail(name);
        if (data.skill) {
          setSkillCache(prev => ({ ...prev, [name]: data.skill! }));
        }
      } catch { /* 静默失败 */ }
    }
    setExpandedSkill(name);
  };

  // 点击工具标签
  const handleToolClick = (name: string) => {
    setExpandedTool(expandedTool === name ? null : name);
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={null}
      width={340}
      styles={{
        body: { background: '#0f172a', color: '#e2e8f0', padding: 0 },
        header: { display: 'none' },
      }}
    >
      {/* 头部 */}
      <div className="market-detail-header">
        <img
          src={getAvatar(npc.name)}
          alt={npc.name}
          className="market-detail-avatar"
          style={{ '--rank-color': rank.color, '--rank-glow': rank.glow } as React.CSSProperties}
        />
        <div className="market-detail-name">
          {npc.name}
          <span style={{
            marginLeft: 8,
            fontSize: 16,
            color: rank.color,
            textShadow: rank.glow,
            fontWeight: 900,
          }}>
            {rank.label}
          </span>
        </div>
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
          综合评分 {stats.overall} · {npc.enabled ? '在线' : '休眠'}
          {npc.llm_channel && ` · ${npc.llm_channel}`}
        </div>
      </div>

      <div style={{ padding: '0 16px 16px' }}>
        {/* 人设描述 */}
        {npc.description && (
          <div className="market-detail-desc" style={{ marginBottom: 12 }}>
            {npc.description}
          </div>
        )}

        {/* 能力属性 */}
        <div className="market-detail-section">
          <div className="market-detail-section-title">能力属性</div>
          {STAT_DEFS.map(def => (
            <div className="market-detail-stat-row" key={def.key}>
              <span className="market-detail-stat-label">{def.icon} {def.label}</span>
              <div className="market-detail-stat-bar">
                <div
                  className="market-detail-stat-fill"
                  style={{ width: `${stats[def.key]}%`, background: def.color }}
                />
              </div>
              <span className="market-detail-stat-value">{stats[def.key]}</span>
            </div>
          ))}
        </div>

        <Divider style={{ borderColor: '#334155', margin: '12px 0' }} />

        {/* 技能 — 可展开详情 */}
        <div className="market-detail-section">
          <div className="market-detail-section-title">装备技能 ({npc.skills.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {npc.skills.length > 0
              ? npc.skills.map(s => (
                  <div key={s}>
                    <span
                      className="market-detail-chip market-detail-chip--skill"
                      onClick={() => handleSkillClick(s)}
                      style={{
                        cursor: 'pointer',
                        borderColor: expandedSkill === s ? '#8b5cf6' : undefined,
                        background: expandedSkill === s ? '#1e1b4b' : undefined,
                      }}
                    >
                      {s} {expandedSkill === s ? '▲' : '▼'}
                    </span>
                    {expandedSkill === s && skillCache[s] && (
                      <div style={expandStyle}>
                        <div style={{ color: '#c4b5fd', fontWeight: 600, marginBottom: 4 }}>
                          {skillCache[s].description}
                        </div>
                        <div style={{ marginBottom: 4 }}>
                          {skillCache[s].tools.map(t => (
                            <span key={t} style={{
                              display: 'inline-block',
                              padding: '1px 6px',
                              margin: '0 4px 2px 0',
                              background: '#334155',
                              borderRadius: 3,
                              fontSize: 10,
                              color: '#7dd3fc',
                            }}>{t}</span>
                          ))}
                        </div>
                        {skillCache[s].prompt_text && (
                          <div style={{ color: '#64748b', fontSize: 10, whiteSpace: 'pre-wrap' }}>
                            {skillCache[s].prompt_text.length > 150
                              ? skillCache[s].prompt_text.slice(0, 150) + '...'
                              : skillCache[s].prompt_text}
                          </div>
                        )}
                      </div>
                    )}
                    {expandedSkill === s && !skillCache[s] && (
                      <div style={{ ...expandStyle, color: '#475569' }}>加载中...</div>
                    )}
                  </div>
                ))
              : <span style={{ color: '#475569', fontSize: 11 }}>暂无技能</span>
            }
          </div>
        </div>

        {/* 工具 — 可展开描述 */}
        <div className="market-detail-section">
          <div className="market-detail-section-title">可用工具 ({npc.tools.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {npc.tools.map(t => (
              <div key={t}>
                <span
                  className="market-detail-chip"
                  onClick={() => handleToolClick(t)}
                  style={{
                    cursor: 'pointer',
                    borderColor: expandedTool === t ? '#3b82f6' : undefined,
                    background: expandedTool === t ? '#172554' : undefined,
                  }}
                >
                  {t} {expandedTool === t ? '▲' : '▼'}
                </span>
                {expandedTool === t && toolMap[t] && (
                  <div style={{ ...expandStyle, borderLeftColor: '#3b82f6' }}>
                    {toolMap[t]}
                  </div>
                )}
                {expandedTool === t && !toolMap[t] && (
                  <div style={{ ...expandStyle, borderLeftColor: '#3b82f6', color: '#475569' }}>
                    {t.startsWith('@') ? '工具组' : '无描述'}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 社交关系 */}
        {npc.groups.length > 0 && (
          <div className="market-detail-section">
            <div className="market-detail-section-title">社交关系 ({npc.groups.length})</div>
            <div className="market-detail-chips">
              {npc.groups.map(g => (
                <span key={g} className="market-detail-chip">{g}</span>
              ))}
            </div>
          </div>
        )}

        <Divider style={{ borderColor: '#334155', margin: '12px 0' }} />

        {/* 数据摘要 */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', fontSize: 11, color: '#94a3b8' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 18, color: '#e2e8f0', fontFamily: 'monospace' }}>{npc.history_count}</div>
            <div>记忆</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 18, color: '#e2e8f0', fontFamily: 'monospace' }}>{npc.tools.length}</div>
            <div>工具</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 18, color: '#e2e8f0', fontFamily: 'monospace' }}>{npc.inventory_count}</div>
            <div>物品</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 18, color: '#e2e8f0', fontFamily: 'monospace' }}>{npc.initiative}/{npc.max_initiative}</div>
            <div>主动值</div>
          </div>
        </div>

        <Divider style={{ borderColor: '#334155', margin: '12px 0' }} />

        {/* 标签 */}
        <Space wrap size={4} style={{ justifyContent: 'center', width: '100%' }}>
          {npc.wechat_status === 'bound' && <Tag color="green">微信已绑定</Tag>}
          {npc.has_mcp && <Tag color="purple">MCP 已配置</Tag>}
          {npc.is_player && <Tag color="blue">玩家角色</Tag>}
          <Tag color={npc.enabled ? 'green' : 'default'}>{npc.enabled ? '在线' : '休眠'}</Tag>
        </Space>

        {/* 操作按钮 */}
        <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <button
            className="market-filter-btn"
            style={{ flex: 1, padding: '6px 0' }}
            onClick={() => onExport(npc.name)}
          >
            导出
          </button>
          <button
            className="market-filter-btn"
            style={{ flex: 1, padding: '6px 0' }}
            onClick={onClose}
          >
            关闭
          </button>
        </div>
      </div>
    </Drawer>
  );
}
