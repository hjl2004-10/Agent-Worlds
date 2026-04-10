import { useState, useEffect, useMemo } from 'react';
import {
  Drawer,
  Tabs,
  Transfer,
  Space,
  Button,
  Input,
  InputNumber,
  Select,
  Tag,
  Tooltip,
  Typography,
  Divider,
  Empty,
  Popconfirm,
  message,
  Badge,
} from 'antd';
import type { TransferProps } from 'antd';
import {
  ToolOutlined,
  AppstoreAddOutlined,
  ApiOutlined,
  LinkOutlined,
  SettingOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  LockOutlined,
} from '@ant-design/icons';
import type { ToolGroup, SkillInfo, MCPServer, MCPManagedServer } from '@/api/types';
import type { MarketplaceMCPServer } from '@/api/types';
import {
  saveToolGroups,
  getMCPServers, createMCPServer, startMCPServer, stopMCPServer, deleteMCPServer,
  getSkillDetail, createSkill, updateSkill, deleteSkill,
  searchMCPMarketplace, installMCPFromMarketplace, importSkillFromUrl,
} from '@/api/god';

const { Text } = Typography;

interface TransferItem {
  key: string;
  title: string;
  description: string;
  disabled?: boolean;
}

interface ToolboxDrawerProps {
  open: boolean;
  onClose: () => void;
  npcName: string;

  // Tools
  allTools: TransferItem[];
  selectedTools: string[];
  onToolsChange: (keys: string[]) => void;

  // Tool Groups
  toolGroups: Record<string, ToolGroup>;
  onToolGroupsChange: (groups: Record<string, ToolGroup>) => void;

  // Skills
  availableSkills: SkillInfo[];
  selectedSkills: string[];
  onSkillsChange: (skills: string[]) => void;
  onSkillsRefresh?: () => void;

  // MCP (per-NPC)
  mcpServers: MCPServer[];
  onMcpServersChange: (servers: MCPServer[]) => void;
}

export function ToolboxDrawer({
  open,
  onClose,
  npcName,
  allTools,
  selectedTools,
  onToolsChange,
  toolGroups,
  onToolGroupsChange,
  availableSkills,
  selectedSkills,
  onSkillsChange,
  onSkillsRefresh,
  mcpServers,
  onMcpServersChange,
}: ToolboxDrawerProps) {
  // Tool group management
  const [editingToolGroup, setEditingToolGroup] = useState<{ name: string; data: ToolGroup } | null>(null);
  const [toolGroupForm, setToolGroupForm] = useState({ name: '', description: '', tools: [] as string[] });
  const [toolGroupsSaving, setToolGroupsSaving] = useState(false);

  // Skill definition CRUD
  const [editingSkillName, setEditingSkillName] = useState<string | null>(null);
  const [skillForm, setSkillForm] = useState({ name: '', description: '', tools: [] as string[], prompt_text: '' });
  const [skillSaving, setSkillSaving] = useState(false);

  // MCP per-NPC
  const [newMcpName, setNewMcpName] = useState('');
  const [newMcpUrl, setNewMcpUrl] = useState('');

  // MCP Manager (global)
  const [managedServers, setManagedServers] = useState<Record<string, MCPManagedServer>>({});
  const [managedLoading, setManagedLoading] = useState(false);
  const [newServerForm, setNewServerForm] = useState({
    name: '',
    command: '',
    args: '',
    transport: 'sse' as 'stdio' | 'sse',
    port: 8100,
    description: '',
  });

  // Marketplace state
  const [mcpSearchQuery, setMcpSearchQuery] = useState('');
  const [mcpSearchResults, setMcpSearchResults] = useState<MarketplaceMCPServer[]>([]);
  const [mcpSearching, setMcpSearching] = useState(false);
  const [mcpInstalling, setMcpInstalling] = useState<string | null>(null);
  const [skillImportUrl, setSkillImportUrl] = useState('');
  const [skillImporting, setSkillImporting] = useState(false);

  // Load managed servers when MCP tab is shown
  const loadManagedServers = async () => {
    setManagedLoading(true);
    try {
      const res = await getMCPServers();
      if (res.data.status === 'ok') {
        setManagedServers(res.data.servers);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setManagedLoading(false);
    }
  };

  useEffect(() => {
    if (open) loadManagedServers();
  }, [open]);

  // ========== Skill-locked tools ==========

  const skillLockedTools = useMemo(() => {
    const locked = new Set<string>();
    for (const skillName of selectedSkills) {
      const skill = availableSkills.find(s => s.name === skillName);
      if (skill) {
        for (const t of skill.tools) locked.add(t);
      }
    }
    return locked;
  }, [selectedSkills, availableSkills]);

  // Effective target keys = user selected + skill locked
  const effectiveTargetKeys = useMemo(() => {
    const set = new Set(selectedTools);
    skillLockedTools.forEach(t => set.add(t));
    return Array.from(set);
  }, [selectedTools, skillLockedTools]);

  // ========== Tool handlers ==========

  const handleToolsChange: TransferProps['onChange'] = (nextTargetKeys) => {
    // Only store manually selected tools (not skill-locked ones)
    const manualTools = (nextTargetKeys as string[]).filter(k => !skillLockedTools.has(k));
    onToolsChange(manualTools);
  };

  const handleAddToolGroup = (groupName: string) => {
    if (selectedTools.includes(groupName)) {
      message.info('该工具组已添加');
      return;
    }
    onToolsChange([...selectedTools, groupName]);
    message.success(`已添加工具组 ${groupName}`);
  };

  const getDisplayTools = (): TransferItem[] => {
    const result: TransferItem[] = allTools.map(t => ({
      ...t,
      disabled: skillLockedTools.has(t.key),
    }));
    for (const [groupName, group] of Object.entries(toolGroups)) {
      result.push({
        key: groupName,
        title: groupName,
        description: `${group.description} (${group.tools.join(', ')})`,
        disabled: skillLockedTools.has(groupName),
      });
    }
    return result;
  };

  // ========== Tool Group handlers ==========

  const openToolGroupEdit = (groupName?: string, groupData?: ToolGroup) => {
    if (groupName && groupData) {
      setEditingToolGroup({ name: groupName, data: groupData });
      setToolGroupForm({
        name: groupName.startsWith('@') ? groupName.slice(1) : groupName,
        description: groupData.description,
        tools: groupData.tools,
      });
    } else {
      setEditingToolGroup(null);
      setToolGroupForm({ name: '', description: '', tools: [] });
    }
  };

  const handleSaveToolGroup = () => {
    if (!toolGroupForm.name.trim()) { message.warning('请输入工具组名称'); return; }
    if (!toolGroupForm.description.trim()) { message.warning('请输入描述'); return; }
    const groupName = toolGroupForm.name.startsWith('@') ? toolGroupForm.name : `@${toolGroupForm.name}`;
    const newGroups = { ...toolGroups };
    if (editingToolGroup && editingToolGroup.name !== groupName) {
      delete newGroups[editingToolGroup.name];
    }
    newGroups[groupName] = { description: toolGroupForm.description, tools: toolGroupForm.tools };
    onToolGroupsChange(newGroups);
    setEditingToolGroup(null);
    setToolGroupForm({ name: '', description: '', tools: [] });
    message.success('工具组已更新');
  };

  const handleDeleteToolGroup = (groupName: string) => {
    const newGroups = { ...toolGroups };
    delete newGroups[groupName];
    onToolGroupsChange(newGroups);
    if (selectedTools.includes(groupName)) {
      onToolsChange(selectedTools.filter(t => t !== groupName));
    }
    message.success('工具组已删除');
  };

  const handleSaveAllToolGroups = async () => {
    setToolGroupsSaving(true);
    try {
      const res = await saveToolGroups(toolGroups);
      if (res.data.status === 'ok') message.success('工具组配置已保存');
      else message.error(res.data.message || '保存失败');
    } catch { message.error('保存失败'); }
    finally { setToolGroupsSaving(false); }
  };

  // ========== Skill definition CRUD ==========

  const resetSkillForm = () => {
    setEditingSkillName(null);
    setSkillForm({ name: '', description: '', tools: [], prompt_text: '' });
  };

  const handleEditSkill = async (name: string) => {
    try {
      const res = await getSkillDetail(name);
      if (res.data.status === 'ok' && res.data.skill) {
        const s = res.data.skill;
        setEditingSkillName(name);
        setSkillForm({
          name: s.name,
          description: s.description,
          tools: s.tools,
          prompt_text: s.prompt_text,
        });
      } else {
        message.error(res.data.message || '获取技能详情失败');
      }
    } catch { message.error('获取技能详情失败'); }
  };

  const handleSaveSkill = async () => {
    if (!skillForm.name.trim()) { message.warning('请输入技能名称'); return; }
    if (!skillForm.description.trim()) { message.warning('请输入描述'); return; }
    setSkillSaving(true);
    try {
      const payload = {
        name: skillForm.name,
        description: skillForm.description,
        tools: skillForm.tools,
        prompt_text: skillForm.prompt_text,
      };
      const res = editingSkillName
        ? await updateSkill(editingSkillName, payload)
        : await createSkill(payload);
      if (res.data.status === 'ok') {
        message.success(res.data.message);
        resetSkillForm();
        onSkillsRefresh?.();
      } else {
        message.error(res.data.message);
      }
    } catch { message.error('保存失败'); }
    finally { setSkillSaving(false); }
  };

  const handleDeleteSkill = async (name: string) => {
    try {
      const res = await deleteSkill(name);
      if (res.data.status === 'ok') {
        message.success(res.data.message);
        // 如果删掉的 skill 正在被 NPC 使用，从选中列表中移除
        if (selectedSkills.includes(name)) {
          onSkillsChange(selectedSkills.filter(s => s !== name));
        }
        onSkillsRefresh?.();
      } else {
        message.error(res.data.message);
      }
    } catch { message.error('删除失败'); }
  };

  // ========== MCP per-NPC handlers ==========

  const handleAddMcpServer = () => {
    if (!newMcpName.trim() || !newMcpUrl.trim()) return;
    onMcpServersChange([...mcpServers, { name: newMcpName.trim(), url: newMcpUrl.trim() }]);
    setNewMcpName('');
    setNewMcpUrl('');
  };

  const handleUseManagedServer = (name: string, url: string) => {
    if (mcpServers.some(s => s.name === name)) {
      message.info(`${name} 已添加`);
      return;
    }
    onMcpServersChange([...mcpServers, { name, url }]);
    message.success(`已添加 ${name}`);
  };

  // ========== MCP Manager handlers ==========

  const handleStartServer = async (name: string) => {
    try {
      const res = await startMCPServer(name);
      if (res.data.status === 'ok') message.success(res.data.message);
      else message.error(res.data.message);
      await loadManagedServers();
    } catch { message.error('启动失败'); }
  };

  const handleStopServer = async (name: string) => {
    try {
      const res = await stopMCPServer(name);
      if (res.data.status === 'ok') message.success(res.data.message);
      else message.error(res.data.message);
      await loadManagedServers();
    } catch { message.error('停止失败'); }
  };

  const handleCreateServer = async () => {
    if (!newServerForm.name.trim() || !newServerForm.command.trim()) {
      message.warning('请填写服务名和命令');
      return;
    }
    try {
      const res = await createMCPServer(newServerForm.name, {
        command: newServerForm.command,
        args: newServerForm.args.split(/\s+/).filter(Boolean),
        transport: newServerForm.transport,
        port: newServerForm.transport === 'sse' ? newServerForm.port : undefined,
        description: newServerForm.description,
      });
      if (res.data.status === 'ok') {
        message.success('服务器已创建');
        setNewServerForm({ name: '', command: '', args: '', transport: 'sse', port: 8100, description: '' });
        await loadManagedServers();
      } else {
        message.error(res.data.message);
      }
    } catch { message.error('创建失败'); }
  };

  const handleDeleteManagedServer = async (name: string) => {
    try {
      const res = await deleteMCPServer(name);
      if (res.data.status === 'ok') message.success(res.data.message);
      else message.error(res.data.message);
      await loadManagedServers();
    } catch { message.error('删除失败'); }
  };

  // ========== Marketplace Handlers ==========

  const handleSearchMCP = async () => {
    if (!mcpSearchQuery.trim()) return;
    setMcpSearching(true);
    try {
      const res = await searchMCPMarketplace(mcpSearchQuery.trim());
      if (res.data.status === 'ok') {
        setMcpSearchResults(res.data.results);
        if (res.data.results.length === 0) message.info('未找到相关 MCP Server');
      } else {
        message.error('搜索失败');
      }
    } catch { message.error('搜索请求失败'); }
    finally { setMcpSearching(false); }
  };

  const handleInstallMCP = async (server: MarketplaceMCPServer) => {
    setMcpInstalling(server.id);
    try {
      const res = await installMCPFromMarketplace(server);
      if (res.data.status === 'ok') {
        message.success(res.data.message);
        await loadManagedServers();
      } else {
        message.error(res.data.message);
      }
    } catch { message.error('安装失败'); }
    finally { setMcpInstalling(null); }
  };

  const handleImportSkill = async () => {
    if (!skillImportUrl.trim()) return;
    setSkillImporting(true);
    try {
      const res = await importSkillFromUrl(skillImportUrl.trim());
      if (res.data.status === 'ok') {
        message.success(res.data.message);
        setSkillImportUrl('');
        onSkillsRefresh?.();
      } else {
        message.error(res.data.message);
      }
    } catch { message.error('导入失败'); }
    finally { setSkillImporting(false); }
  };

  // ========== Render ==========

  const tabItems = [
    // Tab 1: Skills (装备技能)
    {
      key: 'skills',
      label: <Space><ApiOutlined />技能</Space>,
      children: (
        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
            技能 = 工具包 + 提示词，左侧可用 / 右侧已装备
          </Text>
          <Transfer
            dataSource={availableSkills.map((skill) => ({
              key: skill.name,
              title: skill.name,
              description: `${skill.description} (${skill.tools.join(', ') || '无工具'})${skill.has_mcp ? ' [MCP]' : ''}`,
            }))}
            titles={['可用技能', '已装备']}
            targetKeys={selectedSkills}
            onChange={(nextTargetKeys) => {
              const next = nextTargetKeys as string[];
              // 找出被卸载的技能
              const removed = selectedSkills.filter(s => !next.includes(s));
              if (removed.length > 0) {
                // 收集被卸载技能的工具
                const removedTools = new Set<string>();
                for (const skillName of removed) {
                  const skill = availableSkills.find(s => s.name === skillName);
                  if (skill) {
                    for (const t of skill.tools) removedTools.add(t);
                  }
                }
                // 但如果某个工具还被其他仍装备的技能使用，不要移除
                for (const skillName of next) {
                  const skill = availableSkills.find(s => s.name === skillName);
                  if (skill) {
                    for (const t of skill.tools) removedTools.delete(t);
                  }
                }
                // 从 selectedTools 中清除
                if (removedTools.size > 0) {
                  onToolsChange(selectedTools.filter(t => !removedTools.has(t)));
                }
              }
              onSkillsChange(next);
            }}
            render={(item) => (
              <span>
                <strong>{item.title}</strong>
                <span style={{ color: 'var(--text-icon-muted)', marginLeft: 8, fontSize: 12 }}>
                  {item.description}
                </span>
              </span>
            )}
            listStyle={{ width: 280, height: 420 }}
            showSearch
            filterOption={(input, option) =>
              (option?.title ?? '').toLowerCase().includes(input.toLowerCase()) ||
              (option?.description ?? '').toLowerCase().includes(input.toLowerCase())
            }
          />
        </div>
      ),
    },

    // Tab 2: Tools (带 skill 锁定)
    {
      key: 'tools',
      label: <Space><ToolOutlined />工具</Space>,
      children: (
        <div>
          {/* Tool group quick buttons */}
          <Space wrap style={{ marginBottom: 8 }}>
            {Object.entries(toolGroups).map(([name, group]) => (
              <Tooltip key={name} title={group.tools.join(', ')}>
                <Button
                  size="small"
                  icon={<AppstoreAddOutlined />}
                  onClick={() => handleAddToolGroup(name)}
                  type={effectiveTargetKeys.includes(name) ? 'primary' : 'default'}
                >
                  {name}
                </Button>
              </Tooltip>
            ))}
          </Space>

          {skillLockedTools.size > 0 && (
            <div style={{ marginBottom: 8, padding: '4px 8px', background: 'var(--bg-panel)', borderRadius: 4, fontSize: 11, color: '#faad14' }}>
              <LockOutlined style={{ marginRight: 4 }} />
              技能锁定的工具不可移除，需先卸载对应技能
            </div>
          )}

          <Transfer
            dataSource={getDisplayTools()}
            titles={['可用工具/组', '已启用']}
            targetKeys={effectiveTargetKeys}
            onChange={handleToolsChange}
            render={(item) => {
              const isLocked = skillLockedTools.has(item.key);
              return (
                <span>
                  {isLocked && <LockOutlined style={{ color: '#faad14', marginRight: 4, fontSize: 11 }} />}
                  <strong style={{ color: isLocked ? '#faad14' : item.key.startsWith('@') ? '#1890ff' : 'var(--text-primary)' }}>
                    {item.title}
                  </strong>
                  {isLocked && <Tag color="gold" style={{ marginLeft: 4, fontSize: 10, lineHeight: '14px', padding: '0 3px' }}>技能</Tag>}
                  <span style={{ color: 'var(--text-icon-muted)', marginLeft: 8, fontSize: 12 }}>
                    {item.description}
                  </span>
                </span>
              );
            }}
            listStyle={{ width: 280, height: 420 }}
            showSearch
            filterOption={(input, option) =>
              (option?.title ?? '').toLowerCase().includes(input.toLowerCase()) ||
              (option?.description ?? '').toLowerCase().includes(input.toLowerCase())
            }
          />
        </div>
      ),
    },

    // Tab 3: Settings (工具组 + 技能定义管理)
    {
      key: 'settings',
      label: <Space><SettingOutlined />设置</Space>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* ====== Section 1: 技能定义管理 ====== */}
          <Text strong style={{ fontSize: 14 }}>技能定义</Text>

          {/* Create/Edit skill form */}
          <div style={{ padding: 12, background: 'var(--bg-panel)', borderRadius: 6, border: '1px solid var(--border-primary)' }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
              {editingSkillName ? `编辑技能: ${editingSkillName}` : '新建技能'}
            </Text>
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Space.Compact style={{ width: '100%' }}>
                <Input
                  placeholder="技能名 (英文，如 programmer)"
                  value={skillForm.name}
                  onChange={(e) => setSkillForm({ ...skillForm, name: e.target.value })}
                  disabled={!!editingSkillName}
                  style={{ width: '40%' }}
                />
                <Input
                  placeholder="描述 (如 文件读写编辑能力)"
                  value={skillForm.description}
                  onChange={(e) => setSkillForm({ ...skillForm, description: e.target.value })}
                />
              </Space.Compact>
              <Select
                mode="multiple"
                placeholder="选择技能包含的工具/工具组"
                value={skillForm.tools}
                onChange={(v) => setSkillForm({ ...skillForm, tools: v })}
                options={[
                  ...Object.keys(toolGroups).map(name => ({ label: `${name} (工具组)`, value: name })),
                  ...allTools.map(t => ({ label: t.title, value: t.key })),
                ]}
                style={{ width: '100%' }}
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
              />
              <Input.TextArea
                placeholder="技能提示词 (prompt.md 内容，装备时注入到 NPC 对话中)"
                value={skillForm.prompt_text}
                onChange={(e) => setSkillForm({ ...skillForm, prompt_text: e.target.value })}
                autoSize={{ minRows: 3, maxRows: 8 }}
              />
              <Space>
                <Button type="primary" loading={skillSaving} onClick={handleSaveSkill}>
                  {editingSkillName ? '更新' : '创建'}
                </Button>
                {editingSkillName && (
                  <Button onClick={resetSkillForm}>取消</Button>
                )}
              </Space>
            </Space>
          </div>

          {/* Existing skills list */}
          <Space direction="vertical" style={{ width: '100%' }} size={8}>
            {availableSkills.map((skill) => (
              <div key={skill.name} style={{ padding: 10, background: 'var(--bg-panel)', borderRadius: 4, border: '1px solid var(--border-primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <Space>
                    <Text strong style={{ color: '#a78bfa', fontSize: 13 }}>{skill.name}</Text>
                    {skill.has_mcp && <Tag color="gold" style={{ fontSize: 10, margin: 0, padding: '0 3px' }}>MCP</Tag>}
                  </Space>
                  <Space size={4}>
                    <Button type="text" size="small" icon={<EditOutlined style={{ fontSize: 12 }} />}
                      onClick={() => handleEditSkill(skill.name)} style={{ color: 'var(--text-icon)', padding: '0 4px' }} />
                    <Popconfirm title="确定删除此技能?" onConfirm={() => handleDeleteSkill(skill.name)} okText="删除" cancelText="取消">
                      <Button type="text" size="small" danger icon={<DeleteOutlined style={{ fontSize: 12 }} />} style={{ padding: '0 4px' }} />
                    </Popconfirm>
                  </Space>
                </div>
                <Text type="secondary" style={{ fontSize: 11 }}>{skill.description}</Text>
                <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {skill.tools.map((t) => (
                    <Tag key={t} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{t}</Tag>
                  ))}
                  {skill.tools.length === 0 && <Text type="secondary" style={{ fontSize: 10 }}>无工具</Text>}
                </div>
              </div>
            ))}
            {availableSkills.length === 0 && <Empty description="暂无技能定义" />}
          </Space>

          <Divider style={{ margin: '8px 0' }} />

          {/* ====== Section 2: 工具组管理 ====== */}
          <Text strong style={{ fontSize: 14 }}>工具组</Text>

          {/* Create/Edit tool group form */}
          <div style={{ padding: 12, background: 'var(--bg-panel)', borderRadius: 6, border: '1px solid var(--border-primary)' }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
              {editingToolGroup ? `编辑: ${editingToolGroup.name}` : '新建工具组'}
            </Text>
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Input
                placeholder="组名 (如 file, navigation)"
                value={toolGroupForm.name}
                onChange={(e) => setToolGroupForm({ ...toolGroupForm, name: e.target.value })}
                disabled={!!editingToolGroup}
                prefix={<span style={{ color: 'var(--text-icon)' }}>@</span>}
              />
              <Input
                placeholder="描述 (如 文件操作组)"
                value={toolGroupForm.description}
                onChange={(e) => setToolGroupForm({ ...toolGroupForm, description: e.target.value })}
              />
              <Select
                mode="multiple"
                placeholder="选择要包含的工具"
                value={toolGroupForm.tools}
                onChange={(v) => setToolGroupForm({ ...toolGroupForm, tools: v })}
                options={allTools.map(t => ({ label: t.title, value: t.key }))}
                style={{ width: '100%' }}
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
              />
              <Space>
                <Button type="primary" onClick={handleSaveToolGroup}>
                  {editingToolGroup ? '更新' : '创建'}
                </Button>
                {editingToolGroup && (
                  <Button onClick={() => { setEditingToolGroup(null); setToolGroupForm({ name: '', description: '', tools: [] }); }}>
                    取消
                  </Button>
                )}
              </Space>
            </Space>
          </div>

          <Button type="primary" loading={toolGroupsSaving} onClick={handleSaveAllToolGroups} block>
            保存工具组到后端
          </Button>

          {/* Existing groups list */}
          <Space direction="vertical" style={{ width: '100%' }} size={8}>
            {Object.entries(toolGroups).map(([name, group]) => (
              <div key={name} style={{ padding: 10, background: 'var(--bg-panel)', borderRadius: 4, border: '1px solid var(--border-primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <Text strong style={{ color: '#a78bfa', fontSize: 13 }}>{name}</Text>
                  <Space size={4}>
                    <Button type="text" size="small" icon={<EditOutlined style={{ fontSize: 12 }} />}
                      onClick={() => openToolGroupEdit(name, group)} style={{ color: 'var(--text-icon)', padding: '0 4px' }} />
                    <Popconfirm title="确定删除此工具组?" onConfirm={() => handleDeleteToolGroup(name)} okText="删除" cancelText="取消">
                      <Button type="text" size="small" danger icon={<DeleteOutlined style={{ fontSize: 12 }} />} style={{ padding: '0 4px' }} />
                    </Popconfirm>
                  </Space>
                </div>
                <Text type="secondary" style={{ fontSize: 11 }}>{group.description}</Text>
                <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {group.tools.slice(0, 4).map((t) => (
                    <Tag key={t} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{t}</Tag>
                  ))}
                  {group.tools.length > 4 && <Tag style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>+{group.tools.length - 4}</Tag>}
                </div>
              </div>
            ))}
            {Object.keys(toolGroups).length === 0 && <Empty description="暂无工具组" />}
          </Space>

          <Divider style={{ margin: '8px 0', borderColor: 'var(--border-primary)' }} />

          {/* ====== Section 3: 在线市场 ====== */}
          <Text strong style={{ fontSize: 14 }}>在线市场</Text>

          {/* MCP Server 搜索 */}
          <div style={{ padding: 12, background: 'var(--bg-panel)', borderRadius: 6, border: '1px solid var(--border-primary)' }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
              搜索 MCP Server (官方注册表)
            </Text>
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="搜索关键词 (如 browser, github, database...)"
                value={mcpSearchQuery}
                onChange={(e) => setMcpSearchQuery(e.target.value)}
                onPressEnter={handleSearchMCP}
              />
              <Button type="primary" onClick={handleSearchMCP} loading={mcpSearching}>
                搜索
              </Button>
            </Space.Compact>

            {mcpSearchResults.length > 0 && (
              <div style={{ marginTop: 12, maxHeight: 300, overflowY: 'auto' }}>
                {mcpSearchResults.map((server) => (
                  <div key={server.id} style={{
                    padding: '8px 12px', marginBottom: 6, background: '#0d1117',
                    borderRadius: 4, border: '1px solid var(--border-primary)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Text strong style={{ fontSize: 13, color: '#58a6ff' }}>
                          {server.title || server.id}
                        </Text>
                        {server.version && (
                          <Tag style={{ marginLeft: 6, fontSize: 10 }}>{server.version}</Tag>
                        )}
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {server.description}
                        </div>
                        <div style={{ marginTop: 4 }}>
                          {server.packages.map((pkg, i) => (
                            <Tag key={i} style={{ fontSize: 10, margin: '0 4px 0 0', padding: '0 4px' }}>
                              {pkg.registry}: {pkg.identifier}
                            </Tag>
                          ))}
                          {server.remotes.map((_, i) => (
                            <Tag key={`r${i}`} color="blue" style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>
                              remote
                            </Tag>
                          ))}
                        </div>
                      </div>
                      <Button
                        size="small"
                        type="primary"
                        loading={mcpInstalling === server.id}
                        onClick={() => handleInstallMCP(server)}
                        style={{ marginLeft: 8 }}
                      >
                        安装
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Skill 导入 */}
          <div style={{ padding: 12, background: 'var(--bg-panel)', borderRadius: 6, border: '1px solid var(--border-primary)' }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
              从 GitHub 导入 Skill
            </Text>
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="GitHub URL (如 https://github.com/user/repo)"
                value={skillImportUrl}
                onChange={(e) => setSkillImportUrl(e.target.value)}
                onPressEnter={handleImportSkill}
              />
              <Button type="primary" onClick={handleImportSkill} loading={skillImporting}>
                导入
              </Button>
            </Space.Compact>
          </div>
        </Space>
      ),
    },

    // Tab 4: MCP
    {
      key: 'mcp',
      label: <Space><LinkOutlined />MCP</Space>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* Per-NPC MCP bindings */}
          <div>
            <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>
              {npcName} 的 MCP 连接
            </Text>
            {mcpServers.length > 0 && (
              <Space direction="vertical" style={{ width: '100%', marginBottom: 8 }}>
                {mcpServers.map((server, idx) => (
                  <div key={idx} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '6px 10px', background: 'var(--bg-panel)', borderRadius: 6, border: '1px solid var(--border-primary)',
                  }}>
                    <Tag color="green" style={{ margin: 0 }}>{server.name}</Tag>
                    <Text style={{ flex: 1, fontSize: 12, color: 'var(--text-placeholder)' }} ellipsis>{server.url}</Text>
                    <Button type="text" size="small" danger icon={<DeleteOutlined />}
                      onClick={() => onMcpServersChange(mcpServers.filter((_, i) => i !== idx))} />
                  </div>
                ))}
              </Space>
            )}
            <Space.Compact style={{ width: '100%' }}>
              <Input placeholder="服务名" value={newMcpName} onChange={(e) => setNewMcpName(e.target.value)} style={{ width: '30%' }} />
              <Input placeholder="地址 (http://...)" value={newMcpUrl} onChange={(e) => setNewMcpUrl(e.target.value)}
                onPressEnter={handleAddMcpServer} />
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAddMcpServer}>添加</Button>
            </Space.Compact>
          </div>

          <Divider style={{ margin: '4px 0' }} />

          {/* Global MCP Server Manager */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <Text strong style={{ fontSize: 13 }}>MCP 服务器管理</Text>
              <Button size="small" icon={<ReloadOutlined />} onClick={loadManagedServers} loading={managedLoading}>
                刷新
              </Button>
            </div>

            {/* Managed server list */}
            <Space direction="vertical" style={{ width: '100%', marginBottom: 12 }} size={8}>
              {Object.entries(managedServers).map(([name, server]) => {
                const isRunning = server.runtime_status === 'running';
                // 推导 URL: 优先用后端返回的，否则根据 transport+port 推导
                const serverUrl = server.url || (server.transport === 'sse' && server.port ? `http://localhost:${server.port}/sse` : null);
                const alreadyBound = mcpServers.some(s => s.name === name);
                return (
                  <div key={name} style={{
                    padding: '8px 12px', background: 'var(--bg-panel)', borderRadius: 6,
                    border: `1px solid ${isRunning ? '#2a4a2a' : 'var(--border-primary)'}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <Space>
                        <Badge status={isRunning ? 'success' : 'default'} />
                        <Text strong style={{ color: isRunning ? '#4ade80' : 'var(--text-primary)' }}>{name}</Text>
                        {server.pid && <Text type="secondary" style={{ fontSize: 10 }}>PID: {server.pid}</Text>}
                        {alreadyBound && <Tag color="green" style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>已绑定</Tag>}
                      </Space>
                      <Space size={4}>
                        {isRunning ? (
                          <Button size="small" danger icon={<PauseCircleOutlined />} onClick={() => handleStopServer(name)}>
                            停止
                          </Button>
                        ) : (
                          <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => handleStartServer(name)}>
                            启动
                          </Button>
                        )}
                        {serverUrl && !alreadyBound && (
                          <Button size="small" onClick={() => handleUseManagedServer(name, serverUrl)}>
                            绑定到 {npcName}
                          </Button>
                        )}
                        <Popconfirm title="确定删除？" onConfirm={() => handleDeleteManagedServer(name)} okText="删除" cancelText="取消">
                          <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      </Space>
                    </div>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {server.description || `${server.command} ${server.args.join(' ')}`}
                    </Text>
                    {serverUrl && (
                      <div><Text type="secondary" style={{ fontSize: 11 }}>{serverUrl}</Text></div>
                    )}
                  </div>
                );
              })}
              {Object.keys(managedServers).length === 0 && !managedLoading && (
                <Empty description="暂无托管的 MCP 服务器" />
              )}
            </Space>

            {/* Add new managed server */}
            <div style={{ padding: 12, background: 'var(--bg-panel)', borderRadius: 6, border: '1px solid var(--border-primary)' }}>
              <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
                注册新的 MCP 服务器
              </Text>
              <Space direction="vertical" style={{ width: '100%' }} size={8}>
                <Space.Compact style={{ width: '100%' }}>
                  <Input placeholder="服务名" value={newServerForm.name}
                    onChange={(e) => setNewServerForm({ ...newServerForm, name: e.target.value })} style={{ width: '35%' }} />
                  <Input placeholder="描述" value={newServerForm.description}
                    onChange={(e) => setNewServerForm({ ...newServerForm, description: e.target.value })} />
                </Space.Compact>
                <Space.Compact style={{ width: '100%' }}>
                  <Input placeholder="命令 (如 python, node)" value={newServerForm.command}
                    onChange={(e) => setNewServerForm({ ...newServerForm, command: e.target.value })} style={{ width: '35%' }} />
                  <Input placeholder="参数 (空格分隔)" value={newServerForm.args}
                    onChange={(e) => setNewServerForm({ ...newServerForm, args: e.target.value })} />
                </Space.Compact>
                <Space>
                  <Select value={newServerForm.transport}
                    onChange={(v) => setNewServerForm({ ...newServerForm, transport: v })}
                    options={[{ label: 'SSE (HTTP)', value: 'sse' }, { label: 'stdio', value: 'stdio' }]}
                    style={{ width: 120 }} />
                  {newServerForm.transport === 'sse' && (
                    <InputNumber placeholder="端口" value={newServerForm.port} min={1} max={65535}
                      onChange={(v) => setNewServerForm({ ...newServerForm, port: v || 8100 })} addonBefore="端口" />
                  )}
                  <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateServer}>
                    注册
                  </Button>
                </Space>
              </Space>
            </div>
          </div>
        </Space>
      ),
    },
  ];

  return (
    <Drawer
      title={
        <Space>
          <ToolOutlined style={{ color: '#a78bfa' }} />
          <span>{npcName} - 工具箱</span>
        </Space>
      }
      placement="right"
      width={640}
      open={open}
      onClose={onClose}
      styles={{
        header: { background: 'var(--bg-panel)', borderBottom: '1px solid var(--border-primary)' },
        body: { background: 'var(--bg-input)', padding: 12 },
      }}
    >
      <Tabs
        defaultActiveKey="skills"
        items={tabItems}
        size="small"
      />
    </Drawer>
  );
}
