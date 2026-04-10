import { useState, useEffect } from 'react';
import {
  Select, Spin, Typography, Space, Tag, Button, Modal,
  Input, Form, Popconfirm, message, Card, InputNumber, Divider,
} from 'antd';
import {
  SettingOutlined, PlusOutlined, DeleteOutlined, EditOutlined,
  StarOutlined, StarFilled, CloudDownloadOutlined, ApiOutlined,
  CheckCircleOutlined, LoadingOutlined,
} from '@ant-design/icons';
import type { LLMChannel } from '@/api/types';
import {
  getLLMChannels,
  createLLMChannel, updateLLMChannel, deleteLLMChannel,
  addLLMModel, deleteLLMModel, updateLLMRouting,
  fetchRemoteModels,
} from '@/api/god';

const { Text } = Typography;

interface ModelConfigProps {
  channel: string | null;
  model: string | null;
  onChange: (llm: { channel: string | null; model: string | null }) => void;
  disabled?: boolean;
}

// ============ 渠道管理弹窗 ============

interface ChannelManagerProps {
  open: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

function ChannelManager({ open, onClose, onRefresh }: ChannelManagerProps) {
  const [channels, setChannels] = useState<LLMChannel[]>([]);
  const [defaultChannel, setDefaultChannel] = useState('');
  const [loading, setLoading] = useState(false);
  const [editingChannel, setEditingChannel] = useState<string | null>(null);
  const [addingChannel, setAddingChannel] = useState(false);
  const [addingModelTo, setAddingModelTo] = useState<string | null>(null);
  // 远程模型获取
  const [fetchingModelsFor, setFetchingModelsFor] = useState<string | null>(null);
  const [remoteModels, setRemoteModels] = useState<Record<string, string[]>>({});

  const [channelForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [modelForm] = Form.useForm();

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await getLLMChannels();
      if (res.data.status === 'ok') {
        setChannels(res.data.channels);
        setDefaultChannel(res.data.default_channel);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) loadData();
  }, [open]);

  // 创建渠道
  const handleCreateChannel = async () => {
    try {
      const values = await channelForm.validateFields();
      const res = await createLLMChannel({
        id: values.id,
        provider: values.provider,
        base_url: values.base_url || '',
        api_key: values.api_key || '',
        default_model: values.default_model || '',
      });
      if (res.data.status === 'ok') {
        message.success(res.data.message);
        setAddingChannel(false);
        channelForm.resetFields();
        loadData();
        onRefresh();
      } else {
        message.error(res.data.message);
      }
    } catch { /* validation */ }
  };

  // 更新渠道
  const handleUpdateChannel = async (channelId: string) => {
    try {
      const values = await editForm.validateFields();
      const payload: Record<string, string> = {};
      if (values.provider) payload.provider = values.provider;
      if (values.base_url !== undefined) payload.base_url = values.base_url;
      if (values.api_key !== undefined) payload.api_key = values.api_key;
      const res = await updateLLMChannel(channelId, payload);
      if (res.data.status === 'ok') {
        message.success(res.data.message);
        setEditingChannel(null);
        loadData();
        onRefresh();
      } else {
        message.error(res.data.message);
      }
    } catch { /* validation */ }
  };

  // 删除渠道
  const handleDeleteChannel = async (channelId: string) => {
    const res = await deleteLLMChannel(channelId);
    if (res.data.status === 'ok') {
      message.success(res.data.message);
      loadData();
      onRefresh();
    } else {
      message.error(res.data.message);
    }
  };

  // 设为默认
  const handleSetDefault = async (channelId: string) => {
    const res = await updateLLMRouting(channelId);
    if (res.data.status === 'ok') {
      message.success(res.data.message);
      setDefaultChannel(channelId);
      onRefresh();
    }
  };

  // 添加模型
  const handleAddModel = async (channelId: string) => {
    try {
      const values = await modelForm.validateFields();
      const res = await addLLMModel(channelId, {
        model_name: values.model_name,
        temperature: values.temperature ?? 0.8,
        max_tokens: values.max_tokens ?? 500,
      });
      if (res.data.status === 'ok') {
        message.success(res.data.message);
        setAddingModelTo(null);
        modelForm.resetFields();
        loadData();
        onRefresh();
      } else {
        message.error(res.data.message);
      }
    } catch { /* validation */ }
  };

  // 删除模型
  const handleDeleteModel = async (channelId: string, modelName: string) => {
    const res = await deleteLLMModel(channelId, modelName);
    if (res.data.status === 'ok') {
      message.success(res.data.message);
      loadData();
      onRefresh();
    } else {
      message.error(res.data.message);
    }
  };

  // 从远程获取模型列表 (验证 key)
  const handleFetchRemoteModels = async (channelId: string) => {
    setFetchingModelsFor(channelId);
    try {
      const res = await fetchRemoteModels(channelId);
      if (res.data.status === 'ok' && res.data.models) {
        setRemoteModels(prev => ({ ...prev, [channelId]: res.data.models! }));
        message.success(`获取到 ${res.data.models.length} 个模型，Key 验证通过`);
      } else {
        message.error(res.data.message || '获取失败');
      }
    } catch (e: any) {
      message.error(`请求失败: ${e.message}`);
    } finally {
      setFetchingModelsFor(null);
    }
  };

  // 从远程列表中快速添加模型
  const handleQuickAddModel = async (channelId: string, modelName: string) => {
    const res = await addLLMModel(channelId, {
      model_name: modelName,
      temperature: 0.8,
      max_tokens: 500,
    });
    if (res.data.status === 'ok') {
      message.success(`已添加 ${modelName}`);
      loadData();
      onRefresh();
    } else {
      message.error(res.data.message);
    }
  };

  return (
    <Modal
      title="LLM 渠道管理"
      open={open}
      onCancel={onClose}
      footer={null}
      width={560}
      styles={{ body: { maxHeight: '65vh', overflowY: 'auto' } }}
    >
      <Spin spinning={loading}>
        {/* 渠道列表 */}
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {channels.map(ch => (
            <Card
              key={ch.id}
              size="small"
              title={
                <Space>
                  {ch.id === defaultChannel ? (
                    <StarFilled style={{ color: '#faad14' }} />
                  ) : (
                    <StarOutlined
                      style={{ cursor: 'pointer', color: '#999' }}
                      onClick={() => handleSetDefault(ch.id)}
                      title="设为默认渠道"
                    />
                  )}
                  <span style={{ fontWeight: 600 }}>{ch.id}</span>
                  <Tag color={ch.provider === 'claude' ? 'blue' : 'green'} style={{ fontSize: 10 }}>
                    {ch.provider}
                  </Tag>
                </Space>
              }
              extra={
                <Space size={4}>
                  <Button
                    type="text" size="small"
                    icon={<EditOutlined />}
                    onClick={() => {
                      setEditingChannel(editingChannel === ch.id ? null : ch.id);
                      editForm.resetFields();
                    }}
                  />
                  <Popconfirm title={`确定删除渠道 "${ch.id}"？`} onConfirm={() => handleDeleteChannel(ch.id)}>
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              }
            >
              {/* 编辑渠道 */}
              {editingChannel === ch.id && (
                <div style={{ marginBottom: 8, padding: 8, background: '#fafafa', borderRadius: 4 }}>
                  <Form form={editForm} size="small" layout="vertical">
                    <Form.Item name="provider" label="Provider" initialValue={ch.provider}>
                      <Select options={[
                        { value: 'openai', label: 'OpenAI 兼容' },
                        { value: 'claude', label: 'Claude 兼容' },
                      ]} />
                    </Form.Item>
                    <Form.Item name="base_url" label="Base URL">
                      <Input placeholder="https://api.example.com" />
                    </Form.Item>
                    <Form.Item name="api_key" label="API Key">
                      <Input.Password placeholder="sk-..." />
                    </Form.Item>
                    <Button type="primary" size="small" onClick={() => handleUpdateChannel(ch.id)}>
                      保存
                    </Button>
                  </Form>
                </div>
              )}

              {/* 模型列表 */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
                {ch.models.map(m => (
                  <Tag
                    key={m}
                    closable
                    onClose={(e) => { e.preventDefault(); handleDeleteModel(ch.id, m); }}
                    color={m === ch.default_model ? 'blue' : undefined}
                  >
                    {m}
                  </Tag>
                ))}

                {/* 手动添加 */}
                <Tag
                  style={{ borderStyle: 'dashed', cursor: 'pointer' }}
                  onClick={() => { setAddingModelTo(addingModelTo === ch.id ? null : ch.id); modelForm.resetFields(); }}
                >
                  <PlusOutlined /> 手动
                </Tag>

                {/* 从远程获取 */}
                <Tag
                  style={{ borderStyle: 'dashed', cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => handleFetchRemoteModels(ch.id)}
                >
                  {fetchingModelsFor === ch.id ? <LoadingOutlined /> : <ApiOutlined />} 获取模型
                </Tag>
              </div>

              {/* 手动添加表单 */}
              {addingModelTo === ch.id && (
                <div style={{ marginTop: 8 }}>
                  <Form form={modelForm} size="small" layout="inline">
                    <Form.Item name="model_name" rules={[{ required: true, message: '模型名' }]}>
                      <Input placeholder="模型名称" style={{ width: 150 }} />
                    </Form.Item>
                    <Form.Item name="temperature" initialValue={0.8}>
                      <InputNumber placeholder="temp" step={0.1} min={0} max={2} style={{ width: 70 }} />
                    </Form.Item>
                    <Form.Item name="max_tokens" initialValue={500}>
                      <InputNumber placeholder="tokens" step={100} min={100} style={{ width: 80 }} />
                    </Form.Item>
                    <Button type="primary" size="small" onClick={() => handleAddModel(ch.id)}>添加</Button>
                    <Button size="small" onClick={() => { setAddingModelTo(null); modelForm.resetFields(); }}>取消</Button>
                  </Form>
                </div>
              )}

              {/* 远程模型列表 - 点击快速添加 */}
              {remoteModels[ch.id] && remoteModels[ch.id].length > 0 && (
                <div style={{ marginTop: 8, padding: 8, background: '#f6ffed', borderRadius: 4, border: '1px solid #b7eb8f' }}>
                  <div style={{ marginBottom: 4 }}>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 4 }} />
                      Key 验证通过 · 点击模型名快速添加
                    </Text>
                    <Button
                      type="link" size="small" style={{ float: 'right', fontSize: 11, padding: 0 }}
                      onClick={() => setRemoteModels(prev => { const next = { ...prev }; delete next[ch.id]; return next; })}
                    >
                      收起
                    </Button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {remoteModels[ch.id].map(m => {
                      const alreadyAdded = ch.models.includes(m);
                      return (
                        <Tag
                          key={m}
                          style={{
                            cursor: alreadyAdded ? 'default' : 'pointer',
                            opacity: alreadyAdded ? 0.5 : 1,
                          }}
                          color={alreadyAdded ? 'default' : 'processing'}
                          onClick={() => !alreadyAdded && handleQuickAddModel(ch.id, m)}
                        >
                          {alreadyAdded ? <CheckCircleOutlined /> : <PlusOutlined />} {m}
                        </Tag>
                      );
                    })}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </Space>

        <Divider style={{ margin: '12px 0' }} />

        {/* 添加新渠道 */}
        {addingChannel ? (
          <Card size="small" title="添加新渠道">
            <Form form={channelForm} size="small" layout="vertical">
              <Form.Item name="id" label="渠道 ID" rules={[{ required: true, message: '请输入渠道 ID' }]}>
                <Input placeholder="如: openai, deepseek, zhipu" />
              </Form.Item>
              <Form.Item name="provider" label="Provider" initialValue="openai">
                <Select options={[
                  { value: 'openai', label: 'OpenAI 兼容' },
                  { value: 'claude', label: 'Claude 兼容' },
                ]} />
              </Form.Item>
              <Form.Item name="base_url" label="Base URL">
                <Input placeholder="https://api.example.com" />
              </Form.Item>
              <Form.Item name="api_key" label="API Key">
                <Input.Password placeholder="sk-..." />
              </Form.Item>
              <Form.Item name="default_model" label="默认模型">
                <Input placeholder="模型名称（可选）" />
              </Form.Item>
              <Space>
                <Button type="primary" onClick={handleCreateChannel}>创建</Button>
                <Button onClick={() => { setAddingChannel(false); channelForm.resetFields(); }}>取消</Button>
              </Space>
            </Form>
          </Card>
        ) : (
          <Button
            type="dashed" block
            icon={<PlusOutlined />}
            onClick={() => setAddingChannel(true)}
          >
            添加渠道
          </Button>
        )}
      </Spin>
    </Modal>
  );
}


// ============ 主组件 ============

export function ModelConfig({ channel, model, onChange, disabled }: ModelConfigProps) {
  const [loading, setLoading] = useState(false);
  const [channels, setChannels] = useState<LLMChannel[]>([]);
  const [defaultChannel, setDefaultChannel] = useState<string>('');
  const [managerOpen, setManagerOpen] = useState(false);

  const loadChannels = async () => {
    setLoading(true);
    try {
      const res = await getLLMChannels();
      if (res.data.status === 'ok') {
        setChannels(res.data.channels);
        setDefaultChannel(res.data.default_channel);
      }
    } catch (err) {
      console.error('加载渠道列表失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadChannels(); }, []);

  const currentChannel = channels.find(c => c.id === channel);
  const models = currentChannel?.models || [];

  const handleChannelChange = (newChannel: string) => {
    const ch = channels.find(c => c.id === newChannel);
    onChange({ channel: newChannel, model: ch?.default_model || null });
  };

  const handleModelChange = (newModel: string) => {
    onChange({ channel, model: newModel });
  };

  // 快速从通用列表获取模型 - 合并所有渠道的模型到下拉
  const handleQuickSelectModel = (value: string) => {
    // value 格式: channelId::modelName
    const [chId, mName] = value.split('::');
    onChange({ channel: chId, model: mName });
  };

  // 构建全局模型快速选择列表
  const allModels = channels.flatMap(ch =>
    ch.models.map(m => ({
      value: `${ch.id}::${m}`,
      label: (
        <Space>
          <span>{m}</span>
          <Tag style={{ fontSize: 10 }}>{ch.id}</Tag>
        </Space>
      ),
      searchText: `${m} ${ch.id}`,
    }))
  );

  if (loading) {
    return <Spin size="small" />;
  }

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 快速选择：所有模型 */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <CloudDownloadOutlined /> 快速选择模型
            </Text>
            <Button
              type="text" size="small"
              icon={<SettingOutlined />}
              onClick={() => setManagerOpen(true)}
            >
              管理渠道
            </Button>
          </div>
          <Select
            value={channel && model ? `${channel}::${model}` : undefined}
            onChange={handleQuickSelectModel}
            placeholder="从所有渠道中选择模型"
            allowClear
            showSearch
            filterOption={(input, option) =>
              (option?.searchText as string || '').toLowerCase().includes(input.toLowerCase())
            }
            style={{ width: '100%' }}
            disabled={disabled}
            options={allModels}
            onClear={() => onChange({ channel: null, model: null })}
          />
        </div>

        <Divider style={{ margin: '4px 0' }}>或分别指定</Divider>

        {/* 渠道选择 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
            LLM 渠道
          </Text>
          <Select
            value={channel || undefined}
            onChange={handleChannelChange}
            placeholder={defaultChannel ? `默认: ${defaultChannel}` : '选择渠道'}
            allowClear
            style={{ width: '100%' }}
            disabled={disabled}
            onClear={() => onChange({ channel: null, model: null })}
            options={channels.map(c => ({
              value: c.id,
              label: (
                <Space>
                  <span>{c.name}</span>
                  <Tag style={{ fontSize: 10 }}>{c.provider}</Tag>
                </Space>
              ),
            }))}
          />
        </div>

        {/* 模型选择 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
            模型
          </Text>
          <Select
            value={model || undefined}
            onChange={handleModelChange}
            placeholder={currentChannel?.default_model || '选择模型'}
            allowClear
            style={{ width: '100%' }}
            disabled={disabled || !channel}
            options={models.map(m => ({
              value: m,
              label: m,
            }))}
          />
        </div>

        {/* 提示信息 */}
        {!channel && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            未选择时将使用系统默认渠道 ({defaultChannel || '未设置'})
          </Text>
        )}
      </Space>

      {/* 渠道管理弹窗 */}
      <ChannelManager
        open={managerOpen}
        onClose={() => setManagerOpen(false)}
        onRefresh={loadChannels}
      />
    </div>
  );
}
