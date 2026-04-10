import type { MarketNPCData } from '@/api/types';

export interface NPCStats {
  skillLevel: number;
  social: number;
  memory: number;
  activity: number;
  overall: number;
}

export interface RankInfo {
  label: string;
  color: string;
  glow: string;
}

/** 从 NPC 数据推算 5 维能力指标 (0-100) */
export function calcStats(npc: MarketNPCData): NPCStats {
  // 技能等级: 每个技能 20 分
  const skillLevel = Math.min(npc.skills.length * 20, 100);

  // 社交能力: groups * 25 + MCP加成 + 微信加成
  const social = Math.min(
    npc.groups.length * 25
    + (npc.has_mcp ? 15 : 0)
    + (npc.wechat_status === 'bound' ? 10 : 0),
    100
  );

  // 记忆深度: sqrt(count) * 10
  const memory = Math.min(Math.floor(Math.sqrt(npc.history_count) * 10), 100);

  // 活跃度: 主动值占比 + 工具数加成
  const maxInit = npc.max_initiative || 5;
  const activity = Math.min(
    Math.max(npc.initiative, 0) / maxInit * 60
    + Math.min(npc.tools.length * 5, 40),
    100
  );

  // 综合评分: 加权平均
  const overall = Math.round(
    skillLevel * 0.3 + social * 0.2 + memory * 0.25 + activity * 0.25
  );

  return { skillLevel, social, memory, activity, overall };
}

/** 综合评分 → 等级 */
export function getRank(score: number): RankInfo {
  if (score >= 90) return { label: 'S', color: '#fbbf24', glow: '0 0 12px #fbbf2480' };
  if (score >= 70) return { label: 'A', color: '#e879f9', glow: '0 0 10px #e879f980' };
  if (score >= 50) return { label: 'B', color: '#38bdf8', glow: '0 0 8px #38bdf880' };
  if (score >= 30) return { label: 'C', color: '#4ade80', glow: '0 0 6px #4ade8060' };
  return { label: 'D', color: '#6b7280', glow: 'none' };
}

/** 属性维度定义 */
export const STAT_DEFS = [
  { key: 'skillLevel' as const, label: '技能', icon: '⚡', color: '#fbbf24' },
  { key: 'social' as const, label: '社交', icon: '🤝', color: '#e879f9' },
  { key: 'memory' as const, label: '记忆', icon: '🧠', color: '#38bdf8' },
  { key: 'activity' as const, label: '活跃', icon: '🔥', color: '#4ade80' },
];
