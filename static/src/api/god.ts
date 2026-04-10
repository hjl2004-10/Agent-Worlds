import client from './client';
import type {
  GodSelectResponse,
  GodMoveResponse,
  GodStatusResponse,
  MemoryResponse,
  RamBufferResponse,
  AvailableToolsResponse,
  NPCToolsResponse,
  LLMChannelsResponse,
  SpritesResponse,
  NPCConfigResponse,
  NPCConfigUpdateRequest,
  NPCCreateRequest,
  NPCCreateResponse,
  ToolGroupsResponse,
  SkillsResponse,
  SkillDetailResponse,
  SkillCreateRequest,
  SkillUpdateRequest,
  MCPServersResponse,
  InventoryResponse,
  InventoryUpdateRequest,
  LoreResponse,
  LoreUpdateRequest,
  MarketplaceMCPServer,
  MarketplaceSkill,
} from './types';

export const godApi = {
  select: (npcName: string) =>
    client.post<GodSelectResponse>(`/god/select/${encodeURIComponent(npcName)}`),

  deselect: (x?: number, y?: number) => {
    const payload = (x !== undefined && y !== undefined) ? { x, y } : {};
    return client.post<GodStatusResponse>('/god/deselect', payload);
  },

  move: (direction: 'up' | 'down' | 'left' | 'right') =>
    client.post<GodMoveResponse>(`/god/move/${direction}`),

  stop: () => client.post<GodMoveResponse>('/god/stop'),

  getStatus: () => client.get<GodStatusResponse>('/god/status'),

  // 获取 NPC 记忆 (持久化的 HJL 数据)
  getMemory: (npcName: string, offset: number = 0, limit: number = 10) =>
    client.get<MemoryResponse>(`/memory/${encodeURIComponent(npcName)}?offset=${offset}&limit=${limit}`),

  // 获取 NPC 实时对话缓存 (ram_buffer)
  getRamBuffer: (npcName: string) =>
    client.get<RamBufferResponse>(`/conversation/ram/${encodeURIComponent(npcName)}`),
};

// 获取所有可用工具
export const getAvailableTools = () =>
  client.get<AvailableToolsResponse>('/tools/available');

// 获取 NPC 的工具配置
export const getNPCTools = (npcName: string) =>
  client.get<NPCToolsResponse>(`/npc/${encodeURIComponent(npcName)}/tools`);

// 设置 NPC 的工具配置
export const setNPCTools = (npcName: string, tools: string[]) =>
  client.post<NPCToolsResponse>(`/npc/${encodeURIComponent(npcName)}/tools`, { tools });

// ============ Skill API ============

// 获取所有可用技能
export const getAvailableSkills = () =>
  client.get<SkillsResponse>('/skills/available');

// 获取单个技能详情
export const getSkillDetail = (name: string) =>
  client.get<SkillDetailResponse>(`/skills/${encodeURIComponent(name)}`);

// 创建技能
export const createSkill = (data: SkillCreateRequest) =>
  client.post<{ status: string; message: string }>('/skills', data);

// 更新技能
export const updateSkill = (name: string, data: SkillUpdateRequest) =>
  client.put<{ status: string; message: string }>(`/skills/${encodeURIComponent(name)}`, data);

// 删除技能
export const deleteSkill = (name: string) =>
  client.delete<{ status: string; message: string }>(`/skills/${encodeURIComponent(name)}`);

// ============ MCP 进程管理 API ============

export const getMCPServers = () =>
  client.get<MCPServersResponse>('/mcp/servers');

export const createMCPServer = (name: string, config: Record<string, unknown>) =>
  client.post('/mcp/servers', { name, ...config });

export const startMCPServer = (name: string) =>
  client.post(`/mcp/servers/${encodeURIComponent(name)}/start`);

export const stopMCPServer = (name: string) =>
  client.post(`/mcp/servers/${encodeURIComponent(name)}/stop`);

export const deleteMCPServer = (name: string) =>
  client.delete(`/mcp/servers/${encodeURIComponent(name)}`);

// ============ 市场 API ============

export const searchMCPMarketplace = (query: string, limit = 20) =>
  client.get<{ status: string; results: MarketplaceMCPServer[]; count: number }>(
    `/marketplace/mcp/search?q=${encodeURIComponent(query)}&limit=${limit}`
  );

export const installMCPFromMarketplace = (serverInfo: MarketplaceMCPServer, customName?: string, installMethod = 'auto') =>
  client.post<{ status: string; message: string; config: unknown }>(
    '/marketplace/mcp/install',
    { server_info: serverInfo, custom_name: customName, install_method: installMethod }
  );

export const searchSkillsMarketplace = (query: string) =>
  client.get<{ status: string; results: MarketplaceSkill[]; count: number }>(
    `/marketplace/skills/search?q=${encodeURIComponent(query)}`
  );

export const importSkillFromUrl = (url: string, name?: string) =>
  client.post<{ status: string; message: string }>(
    '/marketplace/skills/import',
    { url, name }
  );

// ============ NPC 配置系统 API ============

// 获取 LLM 渠道列表
export const getLLMChannels = () =>
  client.get<LLMChannelsResponse>('/llm/channels');

// ============ LLM 渠道管理 API ============

export const createLLMChannel = (data: { id: string; provider: string; base_url: string; api_key: string; default_model?: string }) =>
  client.post<{ status: string; message: string }>('/llm/channels', data);

export const updateLLMChannel = (channelId: string, data: { provider?: string; base_url?: string; api_key?: string; default_model?: string }) =>
  client.put<{ status: string; message: string }>(`/llm/channels/${encodeURIComponent(channelId)}`, data);

export const deleteLLMChannel = (channelId: string) =>
  client.delete<{ status: string; message: string }>(`/llm/channels/${encodeURIComponent(channelId)}`);

export const addLLMModel = (channelId: string, data: { model_name: string; temperature?: number; max_tokens?: number }) =>
  client.post<{ status: string; message: string }>(`/llm/channels/${encodeURIComponent(channelId)}/models`, data);

export const deleteLLMModel = (channelId: string, modelName: string) =>
  client.delete<{ status: string; message: string }>(`/llm/channels/${encodeURIComponent(channelId)}/models/${encodeURIComponent(modelName)}`);

export const fetchRemoteModels = (channelId: string) =>
  client.get<{ status: string; models?: string[]; message?: string }>(`/llm/channels/${encodeURIComponent(channelId)}/fetch-models`);

export const updateLLMRouting = (defaultChannel: string) =>
  client.put<{ status: string; message: string }>('/llm/routing', { default_channel: defaultChannel });

// 获取精灵列表
export const getSprites = () =>
  client.get<SpritesResponse>('/sprites');

// 获取 NPC 完整配置
export const getNPCConfig = (npcName: string) =>
  client.get<NPCConfigResponse>(`/npc/${encodeURIComponent(npcName)}/config`);

// 更新 NPC 配置
export const updateNPCConfig = (npcName: string, config: NPCConfigUpdateRequest) =>
  client.post<NPCConfigResponse>(`/npc/${encodeURIComponent(npcName)}/config`, config);

// 创建新 NPC
export const createNPC = (data: NPCCreateRequest) =>
  client.post<NPCCreateResponse>('/npc/create', data);

// ============ 工具组 API ============

// 获取工具组列表
export const getToolGroups = () =>
  client.get<ToolGroupsResponse>('/tool-groups');

// 保存工具组配置
export const saveToolGroups = (groups: Record<string, { description: string; tools: string[] }>) =>
  client.post<ToolGroupsResponse>('/tool-groups', { groups });

// ============ 背包系统 API ============

// 获取 NPC 背包
export const getInventory = (npcName: string) =>
  client.get<InventoryResponse>(`/inventory/${encodeURIComponent(npcName)}`);

// 更新 NPC 背包 (管理员操作)
export const updateInventory = (npcName: string, data: InventoryUpdateRequest) =>
  client.post<InventoryResponse>(`/inventory/${encodeURIComponent(npcName)}`, data);

// ============ 世界观系统 API ============

// 获取世界观
export const getLore = () =>
  client.get<LoreResponse>('/world/lore');

// 更新世界观
export const updateLore = (lore: LoreUpdateRequest) =>
  client.post<LoreResponse>('/world/lore', lore);

// ============ 定时器系统 API ============

export interface Timer {
  id: string;
  name: string;
  description: string;
  target: string;
  interval_ticks: number;
  max_triggers: number;
  triggered_count: number;
  last_trigger_tick: number;
  enabled: boolean;
}

export interface TimerCreateRequest {
  name: string;
  description: string;
  target: string;
  interval_ticks?: number;
  max_triggers?: number;
}

// 获取所有定时器
export const getTimers = () =>
  client.get<{ status: string; timers: Timer[] }>('/timers');

// 获取 NPC 的定时器
export const getNPCTimers = (npcName: string) =>
  client.get<{ status: string; npc: string; timers: Timer[] }>(`/timers/${encodeURIComponent(npcName)}`);

// 创建定时器
export const createTimer = (data: TimerCreateRequest) =>
  client.post<{ status: string; timer: Timer }>('/timers/create', data);

// 删除定时器
export const deleteTimer = (timerId: string) =>
  client.delete<{ status: string; message: string }>(`/timers/${timerId}`);

// 更新定时器
export const updateTimer = (timerId: string, data: Partial<Timer>) =>
  client.patch<{ status: string; message: string }>(`/timers/${timerId}`, data);

// ============ NPC 市场 API ============

import type {
  MarketResponse,
  NPCExportRequest,
  NPCExportResponse,
  NPCImportRequest,
  NPCImportResponse,
} from './types';

// 获取市场展示数据
export const getMarketNPCs = () =>
  client.get<MarketResponse>('/npc/market');

// 导出 NPC (单个或批量)
export const exportNPCs = (names: string[]) =>
  client.post<NPCExportResponse>('/npc/export', { names } as NPCExportRequest);

// 导入 NPC (单个或批量)
export const importNPCs = (npcs: NPCImportRequest['npcs'], overwrite: boolean = false) =>
  client.post<NPCImportResponse>('/npc/import', { npcs, overwrite } as NPCImportRequest);

// ============ NPC 启用/禁用 API ============

export interface NPCEnabledResponse {
  status: 'ok' | 'error';
  npc?: string;
  enabled?: boolean;
  message?: string;
}

// 设置 NPC 启用/禁用状态
export const setNPCEnabled = (npcName: string, enabled: boolean) =>
  client.patch<NPCEnabledResponse>(`/npc/${encodeURIComponent(npcName)}/enabled`, { enabled });
