import { useState, useEffect } from 'react';
import {
  Space,
  Button,
  Typography,
  Tag,
  Modal,
  Form,
  Select,
  Divider,
  Spin,
  message,
  Drawer,
} from 'antd';
import {
  ToolOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { getToolGroups, saveToolGroups, getAvailableTools } from '@/api/god';
import type { ToolGroup, AvailableTool } from '@/api/types';
import { useT } from '@/i18n';

const { Text } = Typography;

interface ToolDetail {
  name: string;
  description: string;
  params: Record<string, {
    type: string;
    description?: string;
    minimum?: number;
    maximum?: number;
    enum?: string[];
    default?: string;
  }>;
  required: string[];
}

export function ToolManager() {
  const t = useT();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [groups, setGroups] = useState<Record<string, ToolGroup>>({});
  const [availableTools, setAvailableTools] = useState<AvailableTool[]>([]);
  const [toolDetails, setToolDetails] = useState<Record<string, ToolDetail>>({});

  // 工具详情抽屉
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);

  // 编辑工具组的模态框
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<{ name: string; data: ToolGroup } | null>(null);
  const [form] = Form.useForm();

  // 加载数据
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [groupsRes, toolsRes, detailsRes] = await Promise.all([
          getToolGroups(),
          getAvailableTools(),
          fetch('/api/tools').then((r) => r.json()),
        ]);

        if (groupsRes.data.status === 'ok') {
          setGroups(groupsRes.data.groups || {});
        }

        if (toolsRes.data.status === 'ok') {
          setAvailableTools(toolsRes.data.tools || []);
        }

        if (detailsRes.status === 'ok') {
          setToolDetails(detailsRes.tools || {});
        }
      } catch (err) {
        message.error(t('common.loadFailed'));
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // 保存工具组
  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await saveToolGroups(groups);
      if (res.data.status === 'ok') {
        message.success(t('toolMgr.saved'));
      } else {
        message.error(res.data.message || t('common.saveFailed'));
      }
    } catch (err) {
      message.error(t('common.saveFailed'));
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  // 打开编辑模态框
  const openEditModal = (groupName?: string, groupData?: ToolGroup) => {
    if (groupName && groupData) {
      setEditingGroup({ name: groupName, data: groupData });
      form.setFieldsValue({
        name: groupName,
        description: groupData.description,
        tools: groupData.tools,
      });
    } else {
      setEditingGroup(null);
      form.resetFields();
    }
    setEditModalOpen(true);
  };

  // 保存编辑
  const handleEditSave = async () => {
    try {
      const values = await form.validateFields();
      const groupName = values.name.startsWith('@') ? values.name : `@${values.name}`;

      const newGroups = { ...groups };
      if (editingGroup && editingGroup.name !== groupName) {
        delete newGroups[editingGroup.name];
      }

      newGroups[groupName] = {
        description: values.description,
        tools: values.tools || [],
      };

      setGroups(newGroups);
      setEditModalOpen(false);
      form.resetFields();
    } catch (err) {
      console.error(err);
    }
  };

  // 删除工具组
  const deleteGroup = (groupName: string) => {
    Modal.confirm({
      title: t('toolMgr.confirmDeleteTitle'),
      content: `${t('toolMgr.confirmDeleteContent')} "${groupName}"?`,
      onOk: () => {
        const newGroups = { ...groups };
        delete newGroups[groupName];
        setGroups(newGroups);
      },
    });
  };

  // 打开工具组详情抽屉
  const openGroupDrawer = (groupName: string) => {
    setSelectedGroup(groupName);
    setDrawerOpen(true);
  };

  // 获取工具详情
  const getToolDetail = (toolName: string): ToolDetail | null => {
    const detail = toolDetails[toolName];
    if (detail) {
      return {
        name: toolName,
        description: detail.description,
        params: detail.params || {},
        required: detail.required || [],
      };
    }
    const tool = availableTools.find((t) => t.id === toolName);
    if (tool) {
      return {
        name: tool.id,
        description: tool.description,
        params: {},
        required: [],
      };
    }
    return null;
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 20 }}>
        <Spin size="small" />
      </div>
    );
  }

  const currentGroup = selectedGroup ? groups[selectedGroup] : null;

  return (
    <div>
      {/* 标题栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Space>
          <ToolOutlined style={{ color: '#a78bfa' }} />
          <Text strong style={{ color: 'var(--text-primary)', fontSize: 12 }}>{t('toolMgr.title')}</Text>
          <Tag color="purple" style={{ fontSize: 10 }}>{Object.keys(groups).length}</Tag>
        </Space>
        <Space size={4}>
          <Button
            type="dashed"
            icon={<PlusOutlined />}
            size="small"
            onClick={() => openEditModal()}
            style={{ fontSize: 11 }}
          >
            {t('toolMgr.new')}
          </Button>
          <Button
            type="primary"
            size="small"
            loading={saving}
            onClick={handleSave}
            style={{ fontSize: 11 }}
          >
            {t('common.save')}
          </Button>
        </Space>
      </div>

      {/* 工具组列表 */}
      <Space direction="vertical" style={{ width: '100%' }} size={4}>
        {Object.entries(groups).map(([name, data]) => (
          <div
            key={name}
            style={{
              padding: '6px 8px',
              background: 'var(--bg-panel)',
              borderRadius: 4,
              border: '1px solid var(--border-primary)',
              cursor: 'pointer',
            }}
            onClick={() => openGroupDrawer(name)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text strong style={{ color: '#a78bfa', fontSize: 12 }}>{name}</Text>
              <Space size={2} onClick={(e) => e.stopPropagation()}>
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined style={{ fontSize: 10 }} />}
                  onClick={() => openEditModal(name, data)}
                  style={{ color: 'var(--text-icon)', padding: '0 4px' }}
                />
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined style={{ fontSize: 10 }} />}
                  onClick={() => deleteGroup(name)}
                  style={{ padding: '0 4px' }}
                />
              </Space>
            </div>
            <Text type="secondary" style={{ fontSize: 10 }}>{data.description}</Text>
            <div style={{ marginTop: 4 }}>
              {data.tools.slice(0, 4).map((t) => (
                <Tag key={t} style={{ fontSize: 9, margin: '1px', padding: '0 4px' }}>{t}</Tag>
              ))}
              {data.tools.length > 4 && (
                <Tag style={{ fontSize: 9, margin: '1px', padding: '0 4px' }}>+{data.tools.length - 4}</Tag>
              )}
            </div>
          </div>
        ))}
        {Object.keys(groups).length === 0 && (
          <Text type="secondary" style={{ fontSize: 11, textAlign: 'center', display: 'block', padding: 10 }}>
            {t('toolMgr.noGroups')}
          </Text>
        )}
      </Space>

      {/* 工具详情抽屉 */}
      <Drawer
        title={
          <Space>
            <ToolOutlined style={{ color: '#a78bfa' }} />
            <span>{selectedGroup}</span>
          </Space>
        }
        placement="right"
        width={360}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        styles={{
          header: { background: 'var(--bg-panel)', borderBottom: '1px solid var(--border-primary)' },
          body: { background: 'var(--bg-input)', padding: 12 },
        }}
      >
        {currentGroup && (
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            <div>
              <Text type="secondary" style={{ fontSize: 11 }}>{t('toolMgr.description')}</Text>
              <Text style={{ color: 'var(--text-primary)', display: 'block', marginTop: 4, fontSize: 13 }}>
                {currentGroup.description}
              </Text>
            </div>

            <Divider style={{ margin: '8px 0' }} />

            <div>
              <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
                {t('toolMgr.containsTools')} ({currentGroup.tools.length})
              </Text>
              <Space direction="vertical" style={{ width: '100%' }} size={6}>
                {currentGroup.tools.map((toolName) => {
                  const detail = getToolDetail(toolName);
                  return (
                    <div
                      key={toolName}
                      style={{
                        padding: 8,
                        background: 'var(--bg-panel)',
                        borderRadius: 4,
                        border: '1px solid var(--border-primary)',
                      }}
                    >
                      <Text strong style={{ color: '#38bdf8', fontSize: 12 }}>{toolName}</Text>
                      {detail && (
                        <>
                          <Text style={{ color: 'var(--text-icon)', fontSize: 11, display: 'block', marginTop: 2 }}>
                            {detail.description}
                          </Text>
                          {Object.keys(detail.params).length > 0 && (
                            <div style={{ marginTop: 4 }}>
                              {Object.entries(detail.params).slice(0, 3).map(([paramName, _param]) => (
                                <Tag key={paramName} style={{ fontSize: 9, margin: '1px' }}>
                                  {paramName}
                                  {detail.required.includes(paramName) && <span style={{ color: '#ef4444' }}>*</span>}
                                </Tag>
                              ))}
                              {Object.keys(detail.params).length > 3 && (
                                <Tag style={{ fontSize: 9, margin: '1px' }}>
                                  +{Object.keys(detail.params).length - 3}
                                </Tag>
                              )}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  );
                })}
              </Space>
            </div>
          </Space>
        )}
      </Drawer>

      {/* 编辑工具组模态框 */}
      <Modal
        title={editingGroup ? `${t('toolMgr.editGroup')}: ${editingGroup.name}` : t('toolMgr.newGroup')}
        open={editModalOpen}
        onOk={handleEditSave}
        onCancel={() => setEditModalOpen(false)}
        okText={t('common.save')}
        cancelText={t('common.cancel')}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('toolMgr.groupName')}
            rules={[
              { required: true, message: t('toolMgr.groupNameRequired') },
              { pattern: /^@?[a-zA-Z0-9_]+$/, message: t('toolMgr.groupNameFormat') },
            ]}
          >
            <Select
              placeholder={t('toolMgr.groupNamePlaceholder')}
              disabled={!!editingGroup}
              showSearch
              allowClear
              options={[
                { label: '@file', value: '@file' },
                { label: '@navigation', value: '@navigation' },
                { label: '@task', value: '@task' },
                { label: '@memory', value: '@memory' },
                { label: '@notify', value: '@notify' },
                { label: '@inventory', value: '@inventory' },
              ]}
            />
          </Form.Item>

          <Form.Item name="description" label={t('toolMgr.descLabel')} rules={[{ required: true, message: t('toolMgr.descRequired') }]}>
            <Select
              placeholder={t('toolMgr.descPlaceholder')}
              showSearch
              allowClear
              options={[
                { label: '@file', value: '@file' },
                { label: '@navigation', value: '@navigation' },
                { label: '@task', value: '@task' },
                { label: '@memory', value: '@memory' },
                { label: '@notify', value: '@notify' },
                { label: '@inventory', value: '@inventory' },
              ]}
            />
          </Form.Item>

          <Form.Item name="tools" label={t('toolMgr.toolsLabel')}>
            <Select
              mode="multiple"
              placeholder={t('toolMgr.toolsPlaceholder')}
              options={availableTools.map((t) => ({ label: t.id, value: t.id }))}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
