import { useState, useEffect } from 'react';
import {
  Modal,
  Tabs,
  Spin,
  message,
  Button,
  Space,
  Select,
  Typography,
  Tag,
  Input,
  Tooltip,
  Popconfirm,
  InputNumber,
  Switch,
} from 'antd';
import {
  SaveOutlined,
  UserOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  ShoppingOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  LockOutlined,
  UnlockOutlined,
  ClockCircleOutlined,
  PoweroffOutlined,
  InfoCircleOutlined,
  ToolOutlined,
  WechatOutlined,
  QrcodeOutlined,
  DisconnectOutlined,
} from '@ant-design/icons';
import type { NPCConfig, ToolGroup, InventoryAttrSchema, SkillInfo, MCPServer } from '@/api/types';
import { getNPCConfig, updateNPCConfig, getSprites, getToolGroups, getInventory, updateInventory, getAvailableTools, getAvailableSkills, setNPCEnabled } from '@/api/god';
import { spriteIdsToOptions } from '@/config/sprites';
import { getNPCTimers, createTimer, deleteTimer, type Timer } from '@/api/god';
import { QRCodeSVG } from 'qrcode.react';
import { ModelConfig } from './ModelConfig';
import { PromptConfig } from './PromptConfig';
import { BehaviorConfig } from './BehaviorConfig';
import { ToolboxDrawer } from './ToolboxDrawer';

/** 微信二维码组件 — 将 iLink 返回的文本内容生成二维码 */
function WechatQRCode({ value }: { value: string }) {
  return (
    <QRCodeSVG
      value={value}
      size={200}
      level="M"
      bgColor="#ffffff"
      fgColor="#000000"
    />
  );
}

const { Text } = Typography;

interface NPCConfigPanelProps {
  npcName: string | null;
  open: boolean;
  onClose: () => void;
  onSave?: () => void;
}

interface TransferItem {
  key: string;
  title: string;
  description: string;
}

export function NPCConfigPanel({ npcName, open, onClose, onSave }: NPCConfigPanelProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<NPCConfig | null>(null);
  const [sprites, setSprites] = useState<string[]>([]);
  const [allTools, setAllTools] = useState<TransferItem[]>([]);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [groups, setGroups] = useState<string[]>([]);
  const [newGroup, setNewGroup] = useState('');
  const [toolGroups, setToolGroups] = useState<Record<string, ToolGroup>>({});

  // 背包状态
  const [inventorySchema, setInventorySchema] = useState<Record<string, InventoryAttrSchema>>({});
  const [inventory, setInventory] = useState<Record<string, string | number>>({});
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<string>('');

  // 新增属性表单
  const [newAttrName, setNewAttrName] = useState('');
  const [newAttrValue, setNewAttrValue] = useState('');
  const [newAttrDesc, setNewAttrDesc] = useState('');
  const [newAttrVisibility, setNewAttrVisibility] = useState<'public' | 'private'>('public');
  const [newAttrWritable, setNewAttrWritable] = useState(true);
  const [newAttrWritableByOthers, setNewAttrWritableByOthers] = useState(false);
  const [newAttrRequiresAuth, setNewAttrRequiresAuth] = useState(false);

  // 定时器状态
  const [timers, setTimers] = useState<Timer[]>([]);
  const [newTimerName, setNewTimerName] = useState('');
  const [newTimerDesc, setNewTimerDesc] = useState('');
  const [newTimerInterval, setNewTimerInterval] = useState(120); // 默认 120 tick = 1小时
  const [newTimerMaxTriggers, setNewTimerMaxTriggers] = useState(-1); // -1 无限

  // Skill & MCP 状态
  const [availableSkills, setAvailableSkills] = useState<SkillInfo[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);

  // 工具箱抽屉
  const [toolboxOpen, setToolboxOpen] = useState(false);

  // 微信绑定状态
  const [wechatStatus, setWechatStatus] = useState<'unbound' | 'qr_pending' | 'bound'>('unbound');
  const [wechatQrUrl, setWechatQrUrl] = useState<string>('');
  const [wechatBotId, setWechatBotId] = useState<string>('');
  const [wechatBinding, setWechatBinding] = useState(false); // 绑定中 loading

  // 加载配置
  useEffect(() => {
    if (!open || !npcName) return;

    const loadData = async () => {
      setLoading(true);
      try {
        // 并行加载配置、精灵列表、工具列表、工具组、背包、技能
        const [configRes, spritesRes, toolsRes, groupsRes, inventoryRes, skillsRes] = await Promise.all([
          getNPCConfig(npcName),
          getSprites(),
          getAvailableTools(),
          getToolGroups(),
          getInventory(npcName),
          getAvailableSkills(),
        ]);

        if (configRes.data.status === 'ok') {
          setConfig(configRes.data.config!);
          setSelectedTools(configRes.data.config!.tools || []);
          setGroups(configRes.data.config!.groups || []);
          setSelectedSkills((configRes.data.config as any)?.skills || []);
          setMcpServers((configRes.data.config as any)?.mcp_servers || []);
        } else {
          message.error(configRes.data.message || '加载配置失败');
        }

        if (spritesRes.data.status === 'ok') {
          setSprites(spritesRes.data.sprites);
        }

        if (toolsRes.data.status === 'ok') {
          setAllTools(
            toolsRes.data.tools.map((t) => ({
              key: t.id,
              title: t.id,
              description: t.description,
            }))
          );
        }

        if (groupsRes.data.status === 'ok') {
          setToolGroups(groupsRes.data.groups);
        }

        if (skillsRes.data.status === 'ok') {
          setAvailableSkills(skillsRes.data.skills);
        }

        if (inventoryRes.data.status === 'ok') {
          setInventorySchema(inventoryRes.data.schema || {});
          setInventory(inventoryRes.data.inventory || {});
        }

        // 加载定时器
        const timersRes = await getNPCTimers(npcName);
        if (timersRes.data.status === 'ok') {
          setTimers(timersRes.data.timers);
        }

        // 加载微信绑定状态
        try {
          const { wechatApi } = await import('@/api/wechat');
          const wcRes = await wechatApi.getStatus(npcName);
          setWechatStatus(wcRes.data.status);
          if (wcRes.data.ilink_bot_id) setWechatBotId(wcRes.data.ilink_bot_id);
        } catch { /* 微信模块不可用则忽略 */ }
      } catch (err) {
        message.error('加载配置失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [open, npcName]);

  // 保存配置（包含背包）
  const handleSave = async () => {
    if (!npcName || !config) return;

    setSaving(true);
    try {
      // 并行保存配置和背包
      const [configRes, inventoryRes] = await Promise.all([
        updateNPCConfig(npcName, {
          sprite_id: config.sprite_id,
          description: config.description,
          prompt: config.prompt,
          extra_prompt: config.extra_prompt,
          tools: selectedTools,
          skills: selectedSkills,
          mcp_servers: mcpServers,
          groups: groups,
          llm: config.llm,
          behavior: config.behavior,
        }),
        updateInventory(npcName, {
          schema: inventorySchema,
          inventory: inventory,
        }),
      ]);

      if (configRes.data.status === 'ok' && inventoryRes.data.status === 'ok') {
        message.success('配置已保存');
        onSave?.();
        onClose();
      } else {
        message.error(configRes.data.message || inventoryRes.data.message || '保存失败');
      }
    } catch (err) {
      message.error('保存失败');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  // 更新配置字段
  const updateConfig = <K extends keyof NPCConfig>(key: K, value: NPCConfig[K]) => {
    if (!config) return;
    setConfig({ ...config, [key]: value });
  };

  // 添加群组
  const handleAddGroup = () => {
    if (newGroup.trim() && !groups.includes(newGroup.trim())) {
      setGroups([...groups, newGroup.trim()]);
      setNewGroup('');
    }
  };

  // 删除群组
  const handleRemoveGroup = (group: string) => {
    setGroups(groups.filter(g => g !== group));
  };

  // ========== 背包相关函数 ==========

  // 添加新属性
  const handleAddAttr = () => {
    if (!newAttrName.trim()) {
      message.warning('请输入属性名称');
      return;
    }
    if (inventorySchema[newAttrName]) {
      message.warning('属性已存在');
      return;
    }
    setInventorySchema(prev => ({
      ...prev,
      [newAttrName]: {
        visibility: newAttrVisibility,
        writable_by_owner: newAttrWritable,
        writable_by_others: newAttrWritableByOthers,
        requires_auth: newAttrRequiresAuth,
        description: newAttrDesc,
      },
    } as Record<string, InventoryAttrSchema>));
    setInventory({
      ...inventory,
      [newAttrName]: newAttrValue,
    });
    // 重置表单
    setNewAttrName('');
    setNewAttrValue('');
    setNewAttrDesc('');
    setNewAttrVisibility('public');
    setNewAttrWritable(true);
    setNewAttrWritableByOthers(false);
    setNewAttrRequiresAuth(false);
    message.success('属性已添加');
  };

  // 删除属性
  const handleDeleteAttr = (key: string) => {
    const newSchema = { ...inventorySchema };
    const newInventory = { ...inventory };
    delete newSchema[key];
    delete newInventory[key];
    setInventorySchema(newSchema);
    setInventory(newInventory);
    message.success('属性已删除');
  };

  // 更新 schema 属性
  const updateSchemaProp = (key: string, prop: keyof InventoryAttrSchema, value: boolean | string) => {
    setInventorySchema({
      ...inventorySchema,
      [key]: {
        ...inventorySchema[key],
        [prop]: value,
      },
    });
  };

  // ========== 定时器相关函数 ==========

  // 添加定时器
  const handleAddTimer = async () => {
    if (!npcName) return;
    if (!newTimerName.trim() || !newTimerDesc.trim()) {
      message.warning('请输入定时器名称和提示内容');
      return;
    }

    try {
      const res = await createTimer({
        name: newTimerName,
        description: newTimerDesc,
        target: npcName,
        interval_ticks: newTimerInterval,
        max_triggers: newTimerMaxTriggers,
      });

      if (res.data.status === 'ok') {
        setTimers([...timers, res.data.timer]);
        setNewTimerName('');
        setNewTimerDesc('');
        setNewTimerInterval(120);
        setNewTimerMaxTriggers(-1);
        message.success('定时器已创建');
      } else {
        message.error('创建失败');
      }
    } catch (err) {
      message.error('创建失败');
      console.error(err);
    }
  };

  // 删除定时器
  const handleDeleteTimer = async (timerId: string) => {
    try {
      const res = await deleteTimer(timerId);
      if (res.data.status === 'ok') {
        setTimers(timers.filter(t => t.id !== timerId));
        message.success('定时器已删除');
      } else {
        message.error('删除失败');
      }
    } catch (err) {
      message.error('删除失败');
      console.error(err);
    }
  };

  // 计算游戏内时间
  const formatInterval = (ticks: number) => {
    if (ticks >= 2880) {
      const days = ticks / 2880;
      return `${days} 天`;
    } else if (ticks >= 120) {
      const hours = ticks / 120;
      return `${hours} 小时`;
    } else {
      return `${ticks} tick`;
    }
  };

  if (loading) {
    return (
      <Modal open={open} onCancel={onClose} footer={null} width={700}>
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
        </div>
      </Modal>
    );
  }

  if (!config) {
    return (
      <Modal open={open} onCancel={onClose} footer={null} width={700}>
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Text type="secondary">无法加载配置</Text>
        </div>
      </Modal>
    );
  }

  return (
    <>
    <Modal
      title={
        <Space>
          <UserOutlined />
          <span>NPC 配置 - {npcName}</span>
          {config.is_player && <Tag color="cyan">玩家</Tag>}
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={750}
      centered
      styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
      footer={[
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button
          key="save"
          type="primary"
          icon={<SaveOutlined />}
          loading={saving}
          onClick={handleSave}
        >
          保存
        </Button>,
      ]}
    >
      <Tabs
        defaultActiveKey="basic"
        items={[
          // 基础设置
          {
            key: 'basic',
            label: (
              <Space>
                <UserOutlined />
                基础设置
              </Space>
            ),
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {/* 启用/禁用 NPC */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: config.enabled ? 'rgba(74, 222, 128, 0.08)' : 'rgba(248, 113, 113, 0.08)', borderRadius: 6, border: `1px solid ${config.enabled ? 'rgba(74, 222, 128, 0.25)' : 'rgba(248, 113, 113, 0.25)'}` }}>
                  <Space>
                    <PoweroffOutlined style={{ color: config.enabled ? '#4ade80' : '#f87171' }} />
                    <Text style={{ color: config.enabled ? '#4ade80' : '#f87171' }}>
                      {config.enabled ? 'NPC 已启用' : 'NPC 已禁用'}
                    </Text>
                    <Tooltip title={config.enabled ? '禁用后 NPC 将停止所有活动' : '启用后 NPC 将恢复正常活动'}>
                      <InfoCircleOutlined style={{ color: 'var(--text-icon-muted)', fontSize: 12 }} />
                    </Tooltip>
                  </Space>
                  <Switch
                    checked={config.enabled}
                    onChange={async (checked) => {
                      try {
                        const res = await setNPCEnabled(npcName!, checked);
                        if (res.data.status === 'ok') {
                          updateConfig('enabled', checked);
                          message.success(checked ? 'NPC 已启用' : 'NPC 已禁用');
                        } else {
                          message.error(res.data.message || '操作失败');
                        }
                      } catch (err) {
                        message.error('操作失败');
                        console.error(err);
                      }
                    }}
                    checkedChildren="启用"
                    unCheckedChildren="禁用"
                  />
                </div>

                {/* 精灵选择 */}
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                    精灵图
                  </Text>
                  <Select
                    value={config.sprite_id}
                    onChange={(value) => {
                      // 忽略分组标题点击
                      if (value.startsWith('__group_')) return;
                      updateConfig('sprite_id', value);
                    }}
                    style={{ width: '100%' }}
                    options={spriteIdsToOptions(sprites)}
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </div>

                {/* 群组关系 */}
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                    群组关系
                  </Text>
                  <Space wrap style={{ marginBottom: 8 }}>
                    {groups.map(g => (
                      <Tag
                        key={g}
                        closable
                        onClose={() => handleRemoveGroup(g)}
                        style={{ marginBottom: 4 }}
                      >
                        {g}
                      </Tag>
                    ))}
                  </Space>
                  <Space.Compact style={{ width: '100%' }}>
                    <Input
                      placeholder="关系:名称 (如 朋友:Alice)"
                      value={newGroup}
                      onChange={(e) => setNewGroup(e.target.value)}
                      onPressEnter={handleAddGroup}
                    />
                    <Button type="primary" onClick={handleAddGroup}>
                      添加
                    </Button>
                  </Space.Compact>
                </div>

                {/* 工具箱入口 */}
                <Button
                  block
                  size="large"
                  icon={<ToolOutlined />}
                  onClick={() => setToolboxOpen(true)}
                  style={{
                    height: 'auto',
                    padding: '12px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    background: 'var(--bg-panel)',
                    border: '1px solid var(--border-primary)',
                    borderRadius: 8,
                  }}
                >
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>配置工具箱</div>
                    <div style={{ fontSize: 11, color: 'var(--text-icon-muted)', fontWeight: 'normal' }}>
                      技能 {selectedSkills.length} 个 · 工具 {selectedTools.length} 个 · MCP {mcpServers.length} 个
                    </div>
                  </div>
                </Button>

                {/* 微信绑定 */}
                <div style={{
                  padding: '12px 16px',
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-primary)',
                  borderRadius: 8,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: wechatQrUrl ? 12 : 0 }}>
                    <Space>
                      <WechatOutlined style={{ color: wechatStatus === 'bound' ? '#07c160' : 'var(--text-icon-muted)', fontSize: 16 }} />
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 500 }}>微信绑定</div>
                        <div style={{ fontSize: 11, color: 'var(--text-icon-muted)' }}>
                          {wechatStatus === 'bound'
                            ? `已绑定 (${wechatBotId.slice(0, 8)}...)`
                            : wechatStatus === 'qr_pending'
                              ? '等待扫码...'
                              : '未绑定'}
                        </div>
                      </div>
                    </Space>
                    <Space>
                      {wechatStatus === 'bound' ? (
                        <Popconfirm
                          title="确定解除微信绑定？"
                          onConfirm={async () => {
                            try {
                              const { wechatApi } = await import('@/api/wechat');
                              await wechatApi.unbind(npcName!);
                              setWechatStatus('unbound');
                              setWechatBotId('');
                              setWechatQrUrl('');
                              message.success('已解除绑定');
                            } catch { message.error('解绑失败'); }
                          }}
                        >
                          <Button size="small" danger icon={<DisconnectOutlined />}>解绑</Button>
                        </Popconfirm>
                      ) : (
                        <Button
                          size="small"
                          type="primary"
                          icon={<QrcodeOutlined />}
                          loading={wechatBinding}
                          disabled={wechatStatus === 'qr_pending'}
                          style={{ background: '#07c160', borderColor: '#07c160' }}
                          onClick={async () => {
                            setWechatBinding(true);
                            try {
                              const { wechatApi } = await import('@/api/wechat');
                              const res = await wechatApi.bind(npcName!);
                              if (res.data.error) {
                                message.error(res.data.error);
                              } else if (res.data.qrcode_url) {
                                setWechatQrUrl(res.data.qrcode_url);
                                setWechatStatus('qr_pending');
                                message.info('请用微信扫描二维码');
                                // 轮询绑定状态
                                const pollId = setInterval(async () => {
                                  try {
                                    const statusRes = await wechatApi.getStatus(npcName!);
                                    if (statusRes.data.status === 'bound') {
                                      clearInterval(pollId);
                                      setWechatStatus('bound');
                                      setWechatBotId(statusRes.data.ilink_bot_id || '');
                                      setWechatQrUrl('');
                                      message.success('微信绑定成功！');
                                    } else if (statusRes.data.status !== 'qr_pending') {
                                      clearInterval(pollId);
                                      setWechatStatus('unbound');
                                      setWechatQrUrl('');
                                    }
                                  } catch { /* ignore */ }
                                }, 3000);
                                // 3分钟超时
                                setTimeout(() => {
                                  clearInterval(pollId);
                                  setWechatQrUrl('');
                                  if (wechatStatus === 'qr_pending') {
                                    setWechatStatus('unbound');
                                    message.warning('二维码已过期');
                                  }
                                }, 180000);
                              }
                            } catch { message.error('获取二维码失败'); }
                            setWechatBinding(false);
                          }}
                        >
                          绑定微信
                        </Button>
                      )}
                    </Space>
                  </div>

                  {/* 二维码显示区 — qrcode_img_content 是文本内容，需要前端生成二维码 */}
                  {wechatQrUrl && (
                    <div style={{
                      textAlign: 'center',
                      padding: 16,
                      background: '#fff',
                      borderRadius: 8,
                    }}>
                      <WechatQRCode value={wechatQrUrl} />
                      <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                        用微信扫码完成绑定
                      </div>
                    </div>
                  )}
                </div>
              </Space>
            ),
          },

          // 提示词配置
          {
            key: 'prompt',
            label: (
              <Space>
                <RobotOutlined />
                提示词
              </Space>
            ),
            children: (
              <PromptConfig
                description={config.description}
                prompt={config.prompt}
                extraPrompt={config.extra_prompt}
                onChange={({ description, prompt, extraPrompt }) => {
                  if (description !== undefined) updateConfig('description', description);
                  if (prompt !== undefined) updateConfig('prompt', prompt);
                  if (extraPrompt !== undefined) updateConfig('extra_prompt', extraPrompt);
                }}
              />
            ),
          },

          // 模型配置
          {
            key: 'model',
            label: (
              <Space>
                <RobotOutlined />
                LLM 模型
              </Space>
            ),
            children: (
              <ModelConfig
                channel={config.llm.channel}
                model={config.llm.model}
                onChange={({ channel, model }) => {
                  updateConfig('llm', { channel, model });
                }}
              />
            ),
          },

          // 行为参数
          {
            key: 'behavior',
            label: (
              <Space>
                <ThunderboltOutlined />
                行为参数
              </Space>
            ),
            children: (
              <BehaviorConfig
                baseInitiative={config.behavior.base_initiative}
                walkIdle={config.behavior.walk_idle}
                walkRandom={config.behavior.walk_random}
                walkLinear={config.behavior.walk_linear}
                noCollision={config.behavior.no_collision || false}
                onChange={(behavior) => {
                  updateConfig('behavior', {
                    ...config.behavior,
                    ...behavior,
                  });
                }}
              />
            ),
          },

          // 背包属性
          {
            key: 'inventory',
            label: (
              <Space>
                <ShoppingOutlined />
                背包
              </Space>
            ),
            children: (
              <div>
                {/* 添加新属性 */}
                <div style={{
                  marginBottom: 16,
                  padding: 12,
                  background: 'var(--bg-input)',
                  borderRadius: 6,
                  border: '1px solid var(--border-primary)'
                }}>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
                    添加新属性
                  </Text>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                    <Input
                      placeholder="属性名"
                      value={newAttrName}
                      onChange={(e) => setNewAttrName(e.target.value)}
                      style={{ width: 100 }}
                      size="small"
                    />
                    <Input
                      placeholder="数值"
                      value={newAttrValue}
                      onChange={(e) => setNewAttrValue(e.target.value)}
                      style={{ width: 80 }}
                      size="small"
                    />
                    <Input
                      placeholder="描述（可选）"
                      value={newAttrDesc}
                      onChange={(e) => setNewAttrDesc(e.target.value)}
                      style={{ width: 150 }}
                      size="small"
                    />
                  </div>
                  <Space wrap>
                    <Tooltip title="公开=别人可见">
                      <Tag
                        color={newAttrVisibility === 'public' ? 'green' : 'orange'}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setNewAttrVisibility(newAttrVisibility === 'public' ? 'private' : 'public')}
                      >
                        {newAttrVisibility === 'public' ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                      </Tag>
                    </Tooltip>
                    <Tooltip title="可写=NPC自己能改">
                      <Tag
                        color={newAttrWritable ? 'blue' : 'default'}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setNewAttrWritable(!newAttrWritable)}
                      >
                        {newAttrWritable ? <UnlockOutlined /> : <LockOutlined />}
                      </Tag>
                    </Tooltip>
                    <Tooltip title="他人可写=别人能改">
                      <Tag
                        color={newAttrWritableByOthers ? 'purple' : 'default'}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setNewAttrWritableByOthers(!newAttrWritableByOthers)}
                      >
                        他
                      </Tag>
                    </Tooltip>
                    <Tooltip title="需授权=修改要授权码">
                      <Tag
                        color={newAttrRequiresAuth ? 'red' : 'default'}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setNewAttrRequiresAuth(!newAttrRequiresAuth)}
                      >
                        {newAttrRequiresAuth ? '授' : '免'}
                      </Tag>
                    </Tooltip>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleAddAttr} size="small">
                      添加
                    </Button>
                  </Space>
                </div>

                {/* 背包网格 */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
                  gap: 8,
                  marginBottom: 16
                }}>
                  {Object.entries(inventorySchema).map(([key, schema]) => (
                    <div
                      key={key}
                      style={{
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: 6,
                        padding: 8,
                        position: 'relative',
                      }}
                    >
                      {/* 删除按钮 */}
                      <Popconfirm
                        title="确定删除?"
                        onConfirm={() => handleDeleteAttr(key)}
                        okText="删除"
                        cancelText="取消"
                      >
                        <Button
                          size="small"
                          danger
                          type="text"
                          icon={<DeleteOutlined />}
                          style={{ position: 'absolute', top: 2, right: 2, opacity: 0.6 }}
                        />
                      </Popconfirm>

                      {/* 属性名 */}
                      <div style={{ marginBottom: 4 }}>
                        <Text strong style={{ color: 'var(--text-primary)', fontSize: 13 }}>{key}</Text>
                      </div>

                      {/* 属性值 */}
                      {editingKey === key ? (
                        <Input
                          value={editingValue}
                          onChange={(e) => setEditingValue(e.target.value)}
                          onBlur={() => {
                            setInventory({ ...inventory, [key]: editingValue });
                            setEditingKey(null);
                          }}
                          onPressEnter={() => {
                            setInventory({ ...inventory, [key]: editingValue });
                            setEditingKey(null);
                          }}
                          autoFocus
                          size="small"
                          style={{ marginBottom: 4 }}
                        />
                      ) : (
                        <div
                          onClick={() => { setEditingKey(key); setEditingValue(String(inventory[key] || '')); }}
                          style={{ cursor: 'pointer', marginBottom: 4 }}
                        >
                          <Text style={{ color: '#fbbf24', fontSize: 16, fontWeight: 'bold' }}>
                            {inventory[key] ?? <Text type="secondary">-</Text>}
                          </Text>
                          <EditOutlined style={{ color: 'var(--text-icon)', marginLeft: 4, fontSize: 10 }} />
                        </div>
                      )}

                      {/* 权限标签 */}
                      <div style={{ display: 'flex', gap: 2, marginTop: 4 }}>
                        <Tooltip title={schema.visibility === 'public' ? '公开' : '私有'}>
                          <Tag
                            color={schema.visibility === 'public' ? 'green' : 'orange'}
                            style={{ fontSize: 10, margin: 0, padding: '0 4px', cursor: 'pointer' }}
                            onClick={() => updateSchemaProp(key, 'visibility', schema.visibility === 'public' ? 'private' : 'public')}
                          >
                            {schema.visibility === 'public' ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                          </Tag>
                        </Tooltip>
                        <Tooltip title={schema.writable_by_owner ? '自己可写' : '自己只读'}>
                          <Tag
                            color={schema.writable_by_owner ? 'blue' : 'default'}
                            style={{ fontSize: 10, margin: 0, padding: '0 4px', cursor: 'pointer' }}
                            onClick={() => updateSchemaProp(key, 'writable_by_owner', !schema.writable_by_owner)}
                          >
                            {schema.writable_by_owner ? <UnlockOutlined /> : <LockOutlined />}
                          </Tag>
                        </Tooltip>
                        <Tooltip title={schema.writable_by_others ? '他人可写' : '他人不可写'}>
                          <Tag
                            color={schema.writable_by_others ? 'purple' : 'default'}
                            style={{ fontSize: 10, margin: 0, padding: '0 4px', cursor: 'pointer' }}
                            onClick={() => updateSchemaProp(key, 'writable_by_others', !schema.writable_by_others)}
                          >
                            他
                          </Tag>
                        </Tooltip>
                        {schema.requires_auth && (
                          <Tag color="red" style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>授</Tag>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* 空状态 */}
                {Object.keys(inventorySchema).length === 0 && (
                  <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-icon)' }}>
                    背包空空如也，添加一些属性吧
                  </div>
                )}

                {/* 提示 */}
                <div style={{ textAlign: 'center', marginTop: 12, color: 'var(--text-icon)', fontSize: 11 }}>
                  修改后点击底部"保存"按钮生效
                </div>
              </div>
            ),
          },

          // 定时器
          {
            key: 'timers',
            label: (
              <Space>
                <ClockCircleOutlined />
                定时器
              </Space>
            ),
            children: (
              <div>
                {/* 添加新定时器 */}
                <div style={{
                  marginBottom: 16,
                  padding: 12,
                  background: 'var(--bg-input)',
                  borderRadius: 6,
                  border: '1px solid var(--border-primary)'
                }}>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
                    创建定时提醒 (120 tick = 1游戏小时, 2880 tick = 1游戏天)
                  </Text>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                    <Input
                      placeholder="定时器名称"
                      value={newTimerName}
                      onChange={(e) => setNewTimerName(e.target.value)}
                      style={{ width: 120 }}
                      size="small"
                    />
                    <Input
                      placeholder="提醒内容 (如: 该喝水了)"
                      value={newTimerDesc}
                      onChange={(e) => setNewTimerDesc(e.target.value)}
                      style={{ flex: 1, minWidth: 150 }}
                      size="small"
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <Tooltip title="触发间隔 (tick)">
                      <InputNumber
                        value={newTimerInterval}
                        onChange={(v) => setNewTimerInterval(v || 120)}
                        min={1}
                        style={{ width: 100 }}
                        size="small"
                        addonBefore="间隔"
                      />
                    </Tooltip>
                    <Tooltip title="-1 = 无限次">
                      <InputNumber
                        value={newTimerMaxTriggers}
                        onChange={(v) => setNewTimerMaxTriggers(v ?? -1)}
                        min={-1}
                        style={{ width: 100 }}
                        size="small"
                        addonBefore="次数"
                      />
                    </Tooltip>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      ({formatInterval(newTimerInterval)})
                    </Text>
                  </div>
                  <Button type="primary" icon={<PlusOutlined />} onClick={handleAddTimer} size="small">
                    创建
                  </Button>
                </div>

                {/* 定时器列表 */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {timers.map((timer) => (
                    <div
                      key={timer.id}
                      style={{
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: 6,
                        padding: 12,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <div style={{ marginBottom: 4 }}>
                          <Text strong style={{ color: 'var(--text-primary)' }}>{timer.name}</Text>
                          {!timer.enabled && (
                            <Tag color="red" style={{ marginLeft: 8 }}>已禁用</Tag>
                          )}
                        </div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {timer.description}
                        </Text>
                        <div style={{ marginTop: 4 }}>
                          <Tag color="blue" style={{ fontSize: 10 }}>
                            每 {formatInterval(timer.interval_ticks)}
                          </Tag>
                          {timer.max_triggers > 0 && (
                            <Tag color="orange" style={{ fontSize: 10 }}>
                              剩余 {timer.max_triggers - timer.triggered_count} 次
                            </Tag>
                          )}
                          {timer.triggered_count > 0 && (
                            <Tag style={{ fontSize: 10 }}>
                              已触发 {timer.triggered_count} 次
                            </Tag>
                          )}
                        </div>
                      </div>
                      <Popconfirm
                        title="确定删除此定时器?"
                        onConfirm={() => handleDeleteTimer(timer.id)}
                        okText="删除"
                        cancelText="取消"
                      >
                        <Button danger size="small" icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </div>
                  ))}
                </div>

                {/* 空状态 */}
                {timers.length === 0 && (
                  <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-icon)' }}>
                    没有定时器，创建一个来提醒 {npcName} 吧
                  </div>
                )}

                {/* 提示 */}
                <div style={{ textAlign: 'center', marginTop: 12, color: 'var(--text-icon)', fontSize: 11 }}>
                  定时器触发时会消耗 NPC 主动值并发起对话
                </div>
              </div>
            ),
          },
        ]}
      />
    </Modal>

    {/* 工具箱抽屉 */}
    <ToolboxDrawer
      open={toolboxOpen}
      onClose={() => setToolboxOpen(false)}
      npcName={npcName!}
      allTools={allTools}
      selectedTools={selectedTools}
      onToolsChange={setSelectedTools}
      toolGroups={toolGroups}
      onToolGroupsChange={setToolGroups}
      availableSkills={availableSkills}
      selectedSkills={selectedSkills}
      onSkillsChange={setSelectedSkills}
      onSkillsRefresh={async () => {
        const res = await getAvailableSkills();
        if (res.data.status === 'ok') setAvailableSkills(res.data.skills);
      }}
      mcpServers={mcpServers}
      onMcpServersChange={setMcpServers}
    />
  </>);
}
