// API 类型定义

// ============ 通用响应 ============
export interface ApiResponse<T = unknown> {
  status: 'ok' | 'error';
  message?: string;
  data?: T;
}

// ============ 系统状态 ============
export interface StatusResponse {
  tick: number;
  npc_count: number;
  date: string;
  time: string;
  period: string;
}

export interface EventResponse {
  event: string;
}

// ============ NPC ============
export interface NPC {
  name: string;
  x: number;
  y: number;
  initiative: number;
  is_talking: boolean;
  is_player: boolean;
  ban_target_uuid: string | null;
  god_controlled: boolean;
  god_move_direction: 'up' | 'down' | 'left' | 'right' | null;
  walk_mode: 'idle' | 'random' | 'linear' | 'to_target';
  sprite_id: string;
  tools: string[];  // NPC 可用的工具列表
  enabled: boolean;
}

// ============ 上帝模式 ============
export interface GodSelectResponse {
  status: 'ok' | 'error';
  selected?: string;
  message?: string;
}

export interface GodMoveResponse {
  status: 'ok' | 'error';
  npc?: string;
  direction?: string;
  message?: string;
}

export interface GodStatusResponse {
  god_mode: boolean;
  selected_npc: string | null;
}

// ============ 对话 ============
export interface ConversationState {
  active: boolean;
  speaker: string | null;
  listener: string | null;
  waiting: boolean;
  is_player_conversation?: boolean;
}

// ============ 任务 ============
export interface Task {
  hint: string;
  source: string;
  tool_hint?: string;
  status: 'pending' | 'done';
}

export interface TaskAssignRequest {
  target: string;
  hint: string;
  tool_hint?: string;
}

export interface TaskAssignResponse {
  status: 'ok' | 'error';
  task?: Task;
  message?: string;
}

export interface TaskListResponse {
  status: 'ok' | 'error';
  npc: string;
  tasks: Task[];
  message?: string;
}

export interface TaskActionResponse {
  status: 'ok' | 'error';
  deleted?: number;
  completed?: number;
  message?: string;
}

// ============ 工具 ============
export interface ToolParam {
  type: string;
  description?: string;
  minimum?: number;
  maximum?: number;
  enum?: string[];
  items?: ToolParam;
  minItems?: number;
  maxItems?: number;
  default?: string;
}

export interface Tool {
  description: string;
  params: Record<string, ToolParam>;
  required: string[];
}

export interface ToolsResponse {
  status: 'ok' | 'error';
  tools: Record<string, Tool>;
}

// 可用工具列表 (简化版)
export interface AvailableTool {
  id: string;
  description: string;
  enabled: boolean;
}

export interface AvailableToolsResponse {
  status: 'ok' | 'error';
  tools: AvailableTool[];
}

// NPC 工具配置
export interface NPCToolsResponse {
  status: 'ok' | 'error';
  npc?: string;
  tools?: string[];
  message?: string;
}

export interface NPCToolsRequest {
  tools: string[];
}

// ============ 玩家输入 ============
export interface PlayerInputRequest {
  player_name: string;
  text: string;
}

export interface PlayerInputResponse {
  status: 'ok' | 'error';
  player?: string;
  message?: string;
}

// ============ 记忆系统 ============
export type MemoryItem = string | { role: string; content: string; source?: string };

export interface MemoryResponse {
  status: 'ok' | 'error';
  npc_name?: string;
  total?: number;
  offset?: number;
  limit?: number;
  has_more?: boolean;
  items?: MemoryItem[];
  message?: string;
}

// 实时对话缓存 (ram_buffer)
export interface RamBufferResponse {
  status: 'ok' | 'error';
  npc_name?: string;
  partner?: string;
  total?: number;
  items?: MemoryItem[];
  message?: string;
}

// ============ NPC 配置系统 ============

// LLM 渠道
export interface LLMChannel {
  id: string;
  name: string;
  models: string[];
  default_model: string;
  provider: string;
}

export interface LLMChannelsResponse {
  status: 'ok' | 'error';
  channels: LLMChannel[];
  default_channel: string;
  default_model: string | null;
}

// 精灵列表
export interface SpritesResponse {
  status: 'ok' | 'error';
  sprites: string[];
}

// Skill 定义
export interface SkillInfo {
  name: string;
  description: string;
  tools: string[];
  has_mcp: boolean;
}

export interface SkillsResponse {
  status: 'ok' | 'error';
  skills: SkillInfo[];
}

// Skill 完整数据 (含 prompt)
export interface SkillDetail {
  name: string;
  description: string;
  tools: string[];
  prompt_text: string;
  has_mcp: boolean;
  mcp_server: Record<string, unknown> | null;
}

export interface SkillDetailResponse {
  status: 'ok' | 'error';
  skill?: SkillDetail;
  message?: string;
}

export interface SkillCreateRequest {
  name: string;
  description: string;
  tools: string[];
  prompt_text?: string;
  mcp_server?: Record<string, unknown> | null;
}

export type SkillUpdateRequest = Partial<Omit<SkillCreateRequest, 'name'>>;

// MCP 服务器配置 (NPC 绑定)
export interface MCPServer {
  url: string;
  name: string;
}

// MCP 托管服务器 (进程管理)
export interface MCPManagedServer {
  command: string;
  args: string[];
  transport: 'stdio' | 'sse';
  port?: number;
  env?: Record<string, string>;
  description: string;
  runtime_status: 'running' | 'stopped' | 'error';
  pid: number | null;
  url: string | null;
}

export interface MCPServersResponse {
  status: 'ok' | 'error';
  servers: Record<string, MCPManagedServer>;
}

// 市场 - MCP Server 搜索结果
export interface MarketplaceMCPServer {
  id: string;
  title: string;
  description: string;
  version: string;
  repository: string;
  packages: { registry: string; identifier: string; version: string; transport: string }[];
  remotes: { type: string; url: string }[];
}

// 市场 - Skill 搜索结果
export interface MarketplaceSkill {
  name: string;
  description: string;
  url: string;
  stars: number;
  source: string;
}

// NPC 完整配置
export interface NPCConfig {
  name: string;
  sprite_id: string;
  description: string;
  prompt: string[];
  tools_prompt: string;
  extra_prompt: string;
  tools: string[];
  skills: string[];
  mcp_servers: MCPServer[];
  groups: string[];
  llm: {
    channel: string | null;
    model: string | null;
  };
  behavior: {
    base_initiative: number;
    walk_idle: number;
    walk_random: number;
    walk_linear: number;
    no_collision: boolean;
  };
  is_player: boolean;
  enabled: boolean;
}

export interface NPCConfigResponse {
  status: 'ok' | 'error';
  config?: NPCConfig;
  message?: string;
}

export interface NPCConfigUpdateRequest {
  sprite_id?: string;
  description?: string;
  prompt?: string[];
  extra_prompt?: string;
  tools?: string[];
  skills?: string[];
  mcp_servers?: MCPServer[];
  groups?: string[];
  llm?: {
    channel?: string | null;
    model?: string | null;
  };
  behavior?: {
    base_initiative?: number;
    walk_idle?: number;
    walk_random?: number;
    walk_linear?: number;
    no_collision?: boolean;
  };
}

// NPC 创建
export interface NPCCreateRequest {
  name: string;
  sprite_id?: string;
  description?: string;
  x?: number;
  y?: number;
  prompt?: string[];
  extra_prompt?: string;
  tools?: string[];
  groups?: string[];
  llm?: {
    channel?: string;
    model?: string;
  };
  behavior?: {
    base_initiative?: number;
    walk_idle?: number;
    walk_random?: number;
    walk_linear?: number;
    no_collision?: boolean;
  };
  is_player?: boolean;
}

export interface NPCCreateResponse {
  status: 'ok' | 'error';
  message?: string;
  npc?: {
    name: string;
    sprite_id: string;
    x: number;
    y: number;
  };
}

// ============ 工具组 ============
export interface ToolGroup {
  description: string;
  tools: string[];
}

export interface ToolGroupsResponse {
  status: 'ok' | 'error';
  groups: Record<string, ToolGroup>;
  message?: string;
}

// ============ 背包系统 ============
export interface InventoryAttrSchema {
  visibility: 'public' | 'private';
  writable_by_owner: boolean;
  writable_by_others: boolean;
  requires_auth: boolean;
}

export interface InventoryResponse {
  status: 'ok' | 'error';
  npc?: string;
  schema?: Record<string, InventoryAttrSchema>;
  inventory?: Record<string, string | number>;
  message?: string;
}

export interface InventoryUpdateRequest {
  schema?: Record<string, InventoryAttrSchema>;
  inventory?: Record<string, string | number>;
}

// ============ 世界观系统 ============
export interface LoreData {
  world_name?: string;
  background?: string;
  rules?: string[];
  history?: string[];
}

export interface LoreResponse {
  status: 'ok' | 'error';
  lore?: LoreData;
  message?: string;
}

export type LoreUpdateRequest = LoreData;

// ============ NPC 导入导出 ============

// NPC 导出请求
export interface NPCExportRequest {
  names: string[];
}

// NPC 导出响应
export interface NPCExportResponse {
  status: 'ok' | 'error';
  exported_count?: number;
  npcs?: NPCExportData[];
  not_found?: string[];
  message?: string;
}

// NPC 导出数据格式 (完整的 HJL 格式)
export interface NPCExportData {
  header: {
    uuid: string;
    name: string;
  };
  position: {
    x: number;
    y: number;
  };
  sprite: {
    id: string;
  };
  attributes: {
    description: string;
    prompt: string[];
    extra_prompt: string;
    tools: string[];
    groups: string[];
    base_initiative: number;
    is_player: boolean;
    inventory_schema: Record<string, unknown>;
    inventory: Record<string, string | number>;
    walk: {
      idle_duration: number;
      random_duration: number;
      linear_duration: number;
    };
    llm_config: {
      channel: string | null;
      model: string | null;
    };
  };
  memory: {
    history: string[];
    note: string;
  };
}

// NPC 导入请求
export interface NPCImportRequest {
  npcs: NPCExportData[];
  overwrite?: boolean;
}

// NPC 导入响应
export interface NPCImportResponse {
  status: 'ok' | 'error';
  imported_count?: number;
  imported?: string[];
  skipped?: string[];
  errors?: string[];
  message?: string;
}

// NPC 市场展示数据 (轻量摘要)
export interface MarketNPCData {
  name: string;
  sprite_id: string;
  description: string;
  skills: string[];
  tools: string[];
  groups: string[];
  initiative: number;
  max_initiative: number;
  history_count: number;
  is_player: boolean;
  enabled: boolean;
  has_mcp: boolean;
  wechat_status: string;
  llm_channel: string | null;
  inventory_count: number;
}

export interface MarketResponse {
  status: 'ok' | 'error';
  npcs: MarketNPCData[];
}
