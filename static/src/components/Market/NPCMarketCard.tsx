import type { MarketNPCData } from '@/api/types';
import { calcStats, getRank, STAT_DEFS } from './MarketStats';
import { useT } from '@/i18n';

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

interface Props {
  npc: MarketNPCData;
  onDetail: (npc: MarketNPCData) => void;
  onExport: (name: string) => void;
}

export function NPCMarketCard({ npc, onDetail, onExport }: Props) {
  const t = useT();
  const stats = calcStats(npc);
  const rank = getRank(stats.overall);

  return (
    <div
      className={`market-card ${!npc.enabled ? 'market-card--disabled' : ''}`}
      style={{ '--card-accent': rank.color, '--card-glow': rank.glow } as React.CSSProperties}
      onClick={() => onDetail(npc)}
    >
      {/* 等级徽章 */}
      <div className="market-rank" style={{ '--rank-color': rank.color } as React.CSSProperties}>
        {rank.label}
      </div>

      {/* 状态灯 */}
      <div className={`market-status ${npc.enabled ? 'market-status--online' : 'market-status--offline'}`} />

      {/* 头像 */}
      <div className="market-avatar">
        <img src={getAvatar(npc.name)} alt={npc.name} />
      </div>

      {/* 名字 */}
      <div className="market-name">{npc.name}</div>

      {/* 主技能 */}
      <div className="market-skill-tag">
        {npc.skills.length > 0
          ? npc.skills.slice(0, 2).map(s => <span key={s}>{s}</span>)
          : <span style={{ color: '#475569' }}>{t('market.noSkill')}</span>
        }
      </div>

      {/* 属性条 */}
      <div className="market-stats">
        {STAT_DEFS.map(def => (
          <div className="market-stat-row" key={def.key}>
            <span className="market-stat-label">{t(def.label)}</span>
            <div className="market-stat-bar">
              <div
                className="market-stat-fill"
                style={{ width: `${stats[def.key]}%`, background: def.color }}
              />
            </div>
            <span className="market-stat-value">{stats[def.key]}</span>
          </div>
        ))}
      </div>

      {/* 标签行 */}
      <div className="market-tags">
        {npc.wechat_status === 'bound' && <span className="market-tag market-tag--wechat">{t('market.wechat')}</span>}
        {npc.has_mcp && <span className="market-tag market-tag--mcp">MCP</span>}
        {npc.is_player && <span className="market-tag market-tag--player">{t('market.player')}</span>}
        {npc.tools.length > 5 && <span className="market-tag market-tag--tools">{t('market.toolExpert')}</span>}
        {npc.history_count > 50 && <span className="market-tag market-tag--veteran">{t('market.veteran')}</span>}
      </div>

      {/* 操作按钮 */}
      <div className="market-actions">
        <button onClick={(e) => { e.stopPropagation(); onDetail(npc); }}>{t('market.detail')}</button>
        <button onClick={(e) => { e.stopPropagation(); onExport(npc.name); }}>{t('common.export')}</button>
      </div>
    </div>
  );
}
