import { useState } from 'react';
import { Tooltip } from 'antd';
import {
  SoundOutlined,
  ControlOutlined,
  SettingOutlined,
  PlusOutlined,
  ShoppingOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { useNPCStore } from '@/store/useNPCStore';
import { useGodStore } from '@/store/useGodStore';
import { NPCConfigPanel } from './NPCConfigPanel';
import { InventoryPanel } from './InventoryPanel';
import { NPCCreator } from './NPCCreator';
import { NPCMarket } from '@/components/Market/NPCMarket';
import { PixelButton } from '@/components/ui';
import type { NPC } from '@/api/types';

const COLORS = ['#4ade80', '#38bdf8', '#e879f9', '#fbbf24', '#f87171'];

const AVATARS = [
  '/ui/avatars/soldier.png',
  '/ui/avatars/hacker.png',
  '/ui/avatars/merchant.png',
  '/ui/avatars/medic.png',
  '/ui/avatars/brawler.png',
  '/ui/avatars/sniper.png',
  '/ui/avatars/scientist.png',
  '/ui/avatars/mechanic.png',
  '/ui/avatars/assassin.png',
  '/ui/avatars/chef.png',
  '/ui/avatars/officer.png',
  '/ui/avatars/robot.png',
];

interface NPCListProps {
  onNPCClick?: (name: string) => void;
}

// 判断 NPC 是否"活跃"
function isActive(npc: NPC, selectedNPC: string | null): boolean {
  return npc.is_talking || npc.is_player || npc.name === selectedNPC || npc.walk_mode === 'to_target';
}

// 状态标签文本和颜色
function getStatusTag(npc: NPC, selectedNPC: string | null): { text: string; color: string } {
  if (npc.name === selectedNPC) return { text: '控制中', color: '#fbbf24' };
  if (npc.is_talking) return { text: '对话中', color: '#38bdf8' };
  if (npc.is_player) return { text: '玩家', color: '#22d3ee' };
  if (!npc.enabled) return { text: '禁用', color: '#4a4a6a' };
  if (npc.walk_mode === 'to_target') return { text: '移动中', color: '#38bdf8' };
  if (npc.initiative < 0) return { text: '疲惫', color: 'var(--text-icon)' };
  return { text: '空闲', color: 'var(--text-muted)' };
}

// 状态指示点颜色
function getDotColor(npc: NPC, selectedNPC: string | null): string {
  if (npc.name === selectedNPC) return '#fbbf24';
  if (npc.is_talking) return '#38bdf8';
  if (!npc.enabled) return '#4a4a6a';
  if (npc.initiative < 0) return '#6b7280';
  return '#4ade80';
}

export function NPCList({ onNPCClick }: NPCListProps) {
  const { npcs, fetch: refreshNPCs } = useNPCStore();
  const { selectedNPC } = useGodStore();
  const [configNPC, setConfigNPC] = useState<string | null>(null);
  const [inventoryNPC, setInventoryNPC] = useState<string | null>(null);
  const [showCreator, setShowCreator] = useState(false);
  const [showMarket, setShowMarket] = useState(false);
  const [activeCollapsed, setActiveCollapsed] = useState(false);
  const [idleCollapsed, setIdleCollapsed] = useState(false);

  const handleConfigClick = (e: React.MouseEvent, npcName: string) => {
    e.stopPropagation();
    setConfigNPC(npcName);
  };

  const handleInventoryClick = (e: React.MouseEvent, npcName: string) => {
    e.stopPropagation();
    setInventoryNPC(npcName);
  };

  // 分组
  const activeNPCs: (NPC & { _idx: number })[] = [];
  const idleNPCs: (NPC & { _idx: number })[] = [];
  npcs.forEach((npc, idx) => {
    if (isActive(npc, selectedNPC)) {
      activeNPCs.push({ ...npc, _idx: idx });
    } else {
      idleNPCs.push({ ...npc, _idx: idx });
    }
  });

  // 活跃卡片 — 大卡片（头像框 + 名字 + 状态 + 详情）
  const renderActiveCard = (npc: NPC & { _idx: number }) => {
    const color = COLORS[npc._idx % COLORS.length];
    const isSelected = npc.name === selectedNPC;
    const tag = getStatusTag(npc, selectedNPC);
    const dotColor = getDotColor(npc, selectedNPC);

    return (
      <div
        key={npc.name}
        onClick={() => onNPCClick?.(npc.name)}
        className="npc-card npc-card--active"
        style={{
          cursor: 'pointer',
          padding: '8px',
          marginBottom: 4,
          borderRadius: 2,
          display: 'flex',
          gap: 8,
          alignItems: 'flex-start',
          position: 'relative',
          background: isSelected ? 'rgba(251,191,36,0.10)' : 'rgba(255,255,255,0.03)',
          border: isSelected ? '1px solid rgba(251,191,36,0.4)' : '1px solid transparent',
          boxShadow: isSelected ? '0 0 8px rgba(251,191,36,0.15)' : 'none',
          transition: 'all 0.2s',
        }}
      >
        {/* 头像框 */}
        <div className="npc-avatar" style={{
          width: 36,
          height: 36,
          flexShrink: 0,
          borderRadius: 2,
          border: `2px solid ${color}40`,
          background: 'var(--bg-input)',
          overflow: 'hidden',
          imageRendering: 'pixelated' as const,
          boxShadow: isSelected ? `0 0 8px ${color}40` : 'none',
        }}>
          <img
            src={AVATARS[npc._idx % AVATARS.length]}
            alt={npc.name}
            style={{ width: '100%', height: '100%', objectFit: 'cover', imageRendering: 'pixelated' }}
          />
        </div>

        {/* 信息区 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* 名字行 */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color, fontSize: 14, fontWeight: 700, lineHeight: 1.2 }}>
              {npc.name}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              {/* 操作按钮 */}
              <span className="npc-card__actions" style={{ display: 'flex', gap: 2, opacity: 0 }}>
                <Tooltip title="配置">
                  <span
                    onClick={(e) => handleConfigClick(e, npc.name)}
                    style={{ color: 'var(--text-icon)', cursor: 'pointer', fontSize: 11, padding: '0 2px' }}
                  >
                    <SettingOutlined />
                  </span>
                </Tooltip>
                <Tooltip title="背包">
                  <span
                    onClick={(e) => handleInventoryClick(e, npc.name)}
                    style={{ color: 'var(--text-icon)', cursor: 'pointer', fontSize: 11, padding: '0 2px' }}
                  >
                    <ShoppingOutlined />
                  </span>
                </Tooltip>
                {(npc.tools?.length > 0) && (
                  <Tooltip title={`${npc.tools.length} 个工具`}>
                    <span
                      onClick={(e) => handleConfigClick(e, npc.name)}
                      style={{ color: '#e879f9', cursor: 'pointer', fontSize: 10, padding: '0 2px' }}
                    >
                      <ToolOutlined />
                    </span>
                  </Tooltip>
                )}
              </span>
              {/* 状态点 */}
              <div className="npc-dot--pulse" style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: dotColor,
                boxShadow: `0 0 6px ${dotColor}80`,
                flexShrink: 0,
              }} />
            </div>
          </div>

          {/* 详情行 */}
          <div style={{ marginTop: 3, display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: 'var(--text-muted)' }}>
            <span>({npc.x.toFixed(0)}, {npc.y.toFixed(0)})</span>
            <span>主动:{npc.initiative}</span>
          </div>

          {/* 状态标签 */}
          <div style={{ marginTop: 3 }}>
            <span style={{
              fontSize: 10,
              color: tag.color,
              background: `${tag.color}18`,
              padding: '1px 6px',
              borderRadius: 2,
              border: `1px solid ${tag.color}30`,
            }}>
              {tag.text}
            </span>
            {npc.is_talking && npc.name !== selectedNPC && (
              <span style={{ marginLeft: 4, color: '#38bdf8', fontSize: 10 }}>
                <SoundOutlined />
              </span>
            )}
            {isSelected && (
              <span style={{ marginLeft: 4, color: '#fbbf24', fontSize: 10 }}>
                <ControlOutlined />
              </span>
            )}
          </div>
        </div>
      </div>
    );
  };

  // 闲置卡片 — 紧凑行（彩色竖条 + 名字 + 灰色状态点）
  const renderIdleCard = (npc: NPC & { _idx: number }) => {
    const color = COLORS[npc._idx % COLORS.length];
    const isSelected = npc.name === selectedNPC;
    const dotColor = getDotColor(npc, selectedNPC);

    return (
      <div
        key={npc.name}
        onClick={() => onNPCClick?.(npc.name)}
        className="npc-card npc-card--idle"
        style={{
          cursor: 'pointer',
          padding: '5px 8px',
          marginBottom: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderLeft: `3px solid ${color}60`,
          background: isSelected ? 'rgba(251,191,36,0.08)' : 'transparent',
          opacity: npc.enabled ? 0.7 : 0.4,
          transition: 'all 0.15s',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color, fontSize: 13, fontWeight: 600 }}>
            {npc.name}
          </span>
          {/* hover 时显示的操作按钮 */}
          <span className="npc-card__actions" style={{ display: 'flex', gap: 2, opacity: 0, fontSize: 10 }}>
            <Tooltip title="配置">
              <span
                onClick={(e) => handleConfigClick(e, npc.name)}
                style={{ color: 'var(--text-icon)', cursor: 'pointer', padding: '0 2px' }}
              >
                <SettingOutlined />
              </span>
            </Tooltip>
            <Tooltip title="背包">
              <span
                onClick={(e) => handleInventoryClick(e, npc.name)}
                style={{ color: 'var(--text-icon)', cursor: 'pointer', padding: '0 2px' }}
              >
                <ShoppingOutlined />
              </span>
            </Tooltip>
          </span>
        </div>
        <div style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: dotColor,
          boxShadow: `0 0 4px ${dotColor}60`,
          flexShrink: 0,
        }} />
      </div>
    );
  };

  // 分组标题
  const renderGroupHeader = (
    label: string,
    count: number,
    collapsed: boolean,
    onToggle: () => void,
  ) => (
    <div
      onClick={onToggle}
      style={{
        cursor: 'pointer',
        padding: '4px 8px',
        margin: '4px 0 2px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: 11,
        color: 'var(--text-secondary)',
        background: 'var(--bg-hover-subtle)',
        borderTop: '1px solid var(--bg-hover)',
        borderBottom: '1px solid var(--bg-hover)',
        userSelect: 'none',
      }}
    >
      <span>
        <span style={{
          display: 'inline-block',
          width: 10,
          fontSize: 8,
          transition: 'transform 0.2s',
          transform: collapsed ? 'rotate(0deg)' : 'rotate(90deg)',
        }}>
          &#9654;
        </span>
        {' '}{label} ({count})
      </span>
    </div>
  );

  return (
    <>
      <div
        style={{
          height: '100%',
          padding: 4,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* 头部按钮 */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
          <PixelButton
            variant="style1"
            size="sm"
            onClick={() => setShowCreator(true)}
            style={{ flex: 1 }}
          >
            <PlusOutlined /> 创建
          </PixelButton>
          <PixelButton
            variant="style2"
            size="sm"
            onClick={() => setShowMarket(true)}
            style={{ flex: 1 }}
          >
            <ShoppingOutlined /> 市场
          </PixelButton>
        </div>

        {/* NPC 列表 */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {/* 活跃组 */}
          {activeNPCs.length > 0 && (
            <>
              {renderGroupHeader('活跃', activeNPCs.length, activeCollapsed, () => setActiveCollapsed(!activeCollapsed))}
              {!activeCollapsed && activeNPCs.map(renderActiveCard)}
            </>
          )}

          {/* 闲置组 */}
          {idleNPCs.length > 0 && (
            <>
              {renderGroupHeader('闲置', idleNPCs.length, idleCollapsed, () => setIdleCollapsed(!idleCollapsed))}
              {!idleCollapsed && idleNPCs.map(renderIdleCard)}
            </>
          )}
        </div>
      </div>

      {/* 弹窗区域 */}
      <NPCConfigPanel
        npcName={configNPC}
        open={!!configNPC}
        onClose={() => setConfigNPC(null)}
        onSave={() => refreshNPCs?.()}
      />

      <InventoryPanel
        npcName={inventoryNPC}
        open={!!inventoryNPC}
        onClose={() => setInventoryNPC(null)}
      />

      <NPCCreator
        open={showCreator}
        onClose={() => setShowCreator(false)}
        onSuccess={() => refreshNPCs?.()}
      />

      <NPCMarket
        open={showMarket}
        onClose={() => setShowMarket(false)}
      />
    </>
  );
}
