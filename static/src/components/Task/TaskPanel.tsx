import { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Input,
  Button,
  Space,
  List,
  Tag,
  Typography,
  message,
  Popconfirm,
  Empty,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  CheckOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useTaskStore } from '@/store/useTaskStore';
import { useNPCStore } from '@/store/useNPCStore';
import { PixelButton } from '@/components/ui';
import { useT } from '@/i18n';

const { Text } = Typography;
const { Option } = Select;

export function TaskPanel() {
  const t = useT();
  const {
    tasks,
    tools,
    selectNPC,
    fetchTools,
    assignTask,
    completeTask,
    deleteTask,
  } = useTaskStore();

  const { npcs } = useNPCStore();

  const [targetNPC, setTargetNPC] = useState<string>('');
  const [taskHint, setTaskHint] = useState('');
  const [selectedTool, setSelectedTool] = useState<string>('');
  const [toolParam, setToolParam] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 加载工具列表
  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  // 显示消息
  const taskStore2 = useTaskStore();
  useEffect(() => {
    if (taskStore2.message) {
      if (taskStore2.message.type === 'success') {
        message.success(taskStore2.message.text);
      } else {
        message.error(taskStore2.message.text);
      }
    }
  }, [taskStore2.message]);

  const handleAssign = async () => {
    if (!targetNPC) {
      message.warning(t('task.warnSelectNPC'));
      return;
    }
    if (!taskHint.trim()) {
      message.warning(t('task.warnDesc'));
      return;
    }

    setSubmitting(true);
    // 根据工具类型生成 tool_hint
    let toolHint: string | undefined;
    if (selectedTool && toolParam) {
      const paramKey = selectedTool === 'goto_location' ? 'location' : 'path';
      toolHint = `${selectedTool}: ${paramKey}=${toolParam}`;
    }

    const success = await assignTask(targetNPC, taskHint.trim(), toolHint);
    if (success) {
      setTaskHint('');
      setSelectedTool('');
      setToolParam('');
    }
    setSubmitting(false);
  };

  const handleComplete = async (hint: string) => {
    if (targetNPC) {
      await completeTask(targetNPC, hint.substring(0, 10));
    }
  };

  const handleDelete = async (hint: string) => {
    if (targetNPC) {
      await deleteTask(targetNPC, hint.substring(0, 10));
    }
  };

  const currentTasks = targetNPC ? (tasks[targetNPC] || []) : [];

  return (
    <Card
      size="small"
      title={<span style={{ color: '#e879f9' }}>{t('task.title')}</span>}
      style={{ background: 'var(--bg-panel)', borderColor: '#e879f9' }}
      headStyle={{ borderColor: '#e879f9', color: '#e879f9', padding: '8px 12px', minHeight: 36 }}
      bodyStyle={{ padding: 12 }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 任务创建表单 */}
        <div>
          <div style={{ marginBottom: 12 }}>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              {t('task.targetNPC')}
            </Text>
            <Select
              placeholder={t('task.selectNPC')}
              value={targetNPC || undefined}
              onChange={(val) => {
                setTargetNPC(val);
                if (val) selectNPC(val);
              }}
              style={{ width: '100%' }}
            >
              {npcs.map((npc) => (
                <Option key={npc.name} value={npc.name}>
                  {npc.name}
                </Option>
              ))}
            </Select>
          </div>

          <div style={{ marginBottom: 12 }}>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              {t('task.description')}
            </Text>
            <Input
              placeholder={t('task.descPlaceholder')}
              value={taskHint}
              onChange={(e) => setTaskHint(e.target.value)}
              onPressEnter={handleAssign}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              {t('task.toolOptional')}
            </Text>
            <Space style={{ width: '100%' }}>
              <Select
                placeholder={t('task.selectTool')}
                value={selectedTool || undefined}
                onChange={setSelectedTool}
                style={{ width: 140 }}
                allowClear
              >
                {Object.entries(tools).map(([name]) => (
                  <Option key={name} value={name}>
                    {name}
                  </Option>
                ))}
              </Select>

              {selectedTool && (
                <Input
                  placeholder={selectedTool === 'goto_location' ? t('task.locationName') : t('task.filePath')}
                  value={toolParam}
                  onChange={(e) => setToolParam(e.target.value)}
                  style={{ width: 160 }}
                />
              )}
            </Space>
          </div>

          <PixelButton
            variant="style2"
            size="md"
            onClick={handleAssign}
            disabled={submitting || !targetNPC || !taskHint.trim()}
            style={{ width: '100%' }}
          >
            <PlusOutlined /> {t('task.assign')}
          </PixelButton>
        </div>

        <Divider style={{ margin: 0 }} />

        {/* 任务列表 */}
        <div style={{ maxHeight: 300, overflowY: 'auto' }}>
          {!targetNPC ? (
            <Empty
              description={t('task.selectNPCList')}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : currentTasks.length === 0 ? (
            <Empty
              description={t('task.noTasks')}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <List
              dataSource={currentTasks}
              renderItem={(task) => (
                <List.Item
                  style={{
                    padding: '10px 12px',
                    background: task.status === 'done' ? 'var(--bg-input)' : 'var(--bg-deep)',
                    borderRadius: 6,
                    marginBottom: 6,
                    opacity: task.status === 'done' ? 0.6 : 1,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ marginBottom: 4 }}>
                      <Tag color={task.status === 'done' ? 'default' : 'purple'} style={{ margin: 0 }}>
                        {task.status === 'done' ? t('task.done') : t('task.pending')}
                      </Tag>
                    </div>
                    <Text style={{ display: 'block', marginBottom: 4 }}>{task.hint}</Text>
                    <Space size="small" wrap>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {t('task.source')} {task.source}
                      </Text>
                      {task.tool_hint && (
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {t('task.tool')} {task.tool_hint}
                        </Text>
                      )}
                    </Space>
                  </div>
                  <Space size="small">
                    {task.status !== 'done' && (
                      <Button
                        size="small"
                        icon={<CheckOutlined />}
                        onClick={() => handleComplete(task.hint)}
                        style={{ color: '#4ade80', borderColor: '#4ade80' }}
                        title={t('task.markDoneTitle')}
                      >
                        {t('task.markDone')}
                      </Button>
                    )}
                    <Popconfirm
                      title={t('task.confirmDelete')}
                      onConfirm={() => handleDelete(task.hint)}
                    >
                      <Button
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        title={t('task.deleteTitle')}
                      />
                    </Popconfirm>
                  </Space>
                </List.Item>
              )}
            />
          )}
        </div>
      </Space>
    </Card>
  );
}
