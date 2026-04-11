import { useState, useEffect, useRef } from 'react';
import { Space, Typography, Select, Input, Tag, Button, Popconfirm, message } from 'antd';
import {
  CloseOutlined,
  PlusOutlined,
  DownOutlined,
  UpOutlined,
  CheckOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useGodStore } from '@/store/useGodStore';
import { useNPCStore } from '@/store/useNPCStore';
import { useConversationStore } from '@/store/useConversationStore';
import { useTaskStore } from '@/store/useTaskStore';
import { useKeyboard } from '@/hooks/useKeyboard';
import { PixelBanner, PixelButton } from '@/components/ui';
import { useT } from '@/i18n';
import { MemoryChat } from './MemoryChat';

const { Text } = Typography;
const { Option } = Select;

export function GodControl() {
  const t = useT();
  const { selectedNPC, isGodMode, deselectNPC, move, stop } = useGodStore();
  const { npcs } = useNPCStore();
  const { active: conversationActive } = useConversationStore();
  const {
    tasks,
    tools,
    fetchTools,
    fetchTasks,
    assignTask,
    completeTask,
    deleteTask,
  } = useTaskStore();

  const [memoryRefreshKey, setMemoryRefreshKey] = useState(0);
  const prevConversationActive = useRef(conversationActive);

  // 任务表单状态
  const [taskExpanded, setTaskExpanded] = useState(false);
  const [taskTarget, setTaskTarget] = useState<string>('');
  const [taskHint, setTaskHint] = useState('');
  const [selectedTool, setSelectedTool] = useState('');
  const [toolParam, setToolParam] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 任务消息反馈
  const taskStore = useTaskStore();
  useEffect(() => {
    if (taskStore.message) {
      if (taskStore.message.type === 'success') {
        message.success(taskStore.message.text);
      } else {
        message.error(taskStore.message.text);
      }
    }
  }, [taskStore.message]);

  useEffect(() => {
    if (prevConversationActive.current && !conversationActive) {
      setMemoryRefreshKey(k => k + 1);
    }
    prevConversationActive.current = conversationActive;
  }, [conversationActive]);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  // 选中 NPC 时自动填充任务目标 + 加载任务列表
  useEffect(() => {
    if (selectedNPC) {
      setTaskTarget(selectedNPC);
      fetchTasks(selectedNPC);
    }
  }, [selectedNPC, fetchTasks]);

  useKeyboard({
    onMove: move,
    onStop: stop,
    onEscape: deselectNPC,
    enabled: isGodMode,
  });

  const allNPCNames = npcs.map(n => n.name);

  const handleAssign = async () => {
    if (!taskTarget) {
      message.warning(t('god.warnSelectNPC'));
      return;
    }
    if (!taskHint.trim()) {
      message.warning(t('god.warnTaskDesc'));
      return;
    }

    setSubmitting(true);
    let toolHint: string | undefined;
    if (selectedTool && toolParam) {
      const paramKey = selectedTool === 'goto_location' ? 'location' : 'path';
      toolHint = `${selectedTool}: ${paramKey}=${toolParam}`;
    }

    const success = await assignTask(taskTarget, taskHint.trim(), toolHint);
    if (success) {
      setTaskHint('');
      setSelectedTool('');
      setToolParam('');
    }
    setSubmitting(false);
  };

  const handleComplete = async (hint: string) => {
    if (taskTarget) {
      await completeTask(taskTarget, hint.substring(0, 10));
    }
  };

  const handleDelete = async (hint: string) => {
    if (taskTarget) {
      await deleteTask(taskTarget, hint.substring(0, 10));
    }
  };

  const currentTasks = taskTarget ? (tasks[taskTarget] || []) : [];

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 标题栏 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <PixelBanner variant="style4" style={{ height: 32 }}>
          <Space size={6}>
            <span style={{ fontSize: 13 }}>{t('god.title')}</span>
            {selectedNPC && (
              <span style={{
                fontSize: 12,
                textShadow: '0 0 8px rgba(251, 191, 36, 0.4)',
              }}>
                {t('god.control')}: <strong>{selectedNPC}</strong>
              </span>
            )}
          </Space>
        </PixelBanner>

        {selectedNPC && (
          <PixelButton variant="style1" size="sm" onClick={deselectNPC} title={t('god.cancelControl')}>
            <CloseOutlined />
          </PixelButton>
        )}
      </div>

      {/* 聊天记录区域 */}
      <div style={{ flex: 1, minHeight: 0 }}>
        {selectedNPC ? (
          <MemoryChat npcName={selectedNPC} allNPCNames={allNPCNames} refreshKey={memoryRefreshKey} />
        ) : (
          <div className="empty-state-text">
            ···  {t('god.viewHistory')}  ···
          </div>
        )}
      </div>

      {/* 任务区域 — 折叠面板 */}
      <div style={{ marginTop: 8, borderTop: '1px solid var(--bg-hover)' }}>
        <div
          onClick={() => setTaskExpanded(!taskExpanded)}
          style={{
            cursor: 'pointer',
            padding: '6px 8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 12,
            color: 'var(--text-secondary)',
            background: 'var(--bg-hover-subtle)',
            userSelect: 'none',
          }}
        >
          <Space size={4}>
            <PlusOutlined style={{ fontSize: 10 }} />
            <span>{t('god.assignTask')}</span>
            {currentTasks.filter(t => t.status !== 'done').length > 0 && (
              <Tag color="purple" style={{ margin: 0, fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>
                {currentTasks.filter(t => t.status !== 'done').length}
              </Tag>
            )}
          </Space>
          {taskExpanded ? <UpOutlined style={{ fontSize: 10 }} /> : <DownOutlined style={{ fontSize: 10 }} />}
        </div>

        {taskExpanded && (
          <div style={{ padding: '8px 6px', maxHeight: 320, overflowY: 'auto' }}>
            {/* 目标 NPC */}
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 3 }}>{t('god.targetNPC')}</Text>
              <Select
                placeholder={t('god.selectTargetNPC')}
                value={taskTarget || undefined}
                onChange={(val) => {
                  setTaskTarget(val);
                  if (val) fetchTasks(val);
                }}
                style={{ width: '100%' }}
                size="small"
              >
                {npcs.map((npc) => (
                  <Option key={npc.name} value={npc.name}>{npc.name}</Option>
                ))}
              </Select>
            </div>

            {/* 任务描述 */}
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 3 }}>{t('god.taskDesc')}</Text>
              <Input
                placeholder={t('god.taskPlaceholder')}
                value={taskHint}
                onChange={(e) => setTaskHint(e.target.value)}
                onPressEnter={handleAssign}
                size="small"
              />
            </div>

            {/* 工具选择 */}
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 3 }}>{t('god.toolOptional')}</Text>
              <div style={{ display: 'flex', gap: 4 }}>
                <Select
                  placeholder={t('god.selectTool')}
                  value={selectedTool || undefined}
                  onChange={setSelectedTool}
                  style={{ width: 130 }}
                  size="small"
                  allowClear
                >
                  {Object.entries(tools).map(([name]) => (
                    <Option key={name} value={name}>{name}</Option>
                  ))}
                </Select>
                {selectedTool && (
                  <Input
                    placeholder={selectedTool === 'goto_location' ? t('god.locationName') : t('god.filePath')}
                    value={toolParam}
                    onChange={(e) => setToolParam(e.target.value)}
                    size="small"
                    style={{ flex: 1 }}
                  />
                )}
              </div>
            </div>

            <PixelButton
              variant="style2"
              size="sm"
              onClick={handleAssign}
              disabled={submitting || !taskTarget || !taskHint.trim()}
              style={{ width: '100%', marginBottom: 8 }}
            >
              <PlusOutlined /> {t('god.assignTask')}
            </PixelButton>

            {/* 当前 NPC 任务列表 */}
            {taskTarget && currentTasks.length > 0 && (
              <div style={{ borderTop: '1px solid var(--bg-hover)', paddingTop: 6 }}>
                <Text type="secondary" style={{ fontSize: 11, marginBottom: 4, display: 'block' }}>
                  {taskTarget}{t('god.tasksOf')} ({currentTasks.length})
                </Text>
                {currentTasks.map((task, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '6px 8px',
                      background: task.status === 'done' ? 'var(--bg-hover-subtle)' : 'var(--bg-hover)',
                      borderRadius: 4,
                      marginBottom: 4,
                      opacity: task.status === 'done' ? 0.6 : 1,
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 6,
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                        <Tag
                          color={task.status === 'done' ? 'default' : 'purple'}
                          style={{ margin: 0, fontSize: 10, lineHeight: '16px', padding: '0 4px' }}
                        >
                          {task.status === 'done' ? t('god.done') : t('god.pending')}
                        </Tag>
                      </div>
                      <Text style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>{task.hint}</Text>
                      <Text type="secondary" style={{ fontSize: 10 }}>
                        {t('god.source')}: {task.source}
                        {task.tool_hint && ` · ${t('activity.tool')}: ${task.tool_hint}`}
                      </Text>
                    </div>
                    <Space size={2} style={{ flexShrink: 0 }}>
                      {task.status !== 'done' && (
                        <Button
                          size="small"
                          type="text"
                          icon={<CheckOutlined style={{ color: '#4ade80', fontSize: 11 }} />}
                          onClick={() => handleComplete(task.hint)}
                          title={t('god.done')}
                          style={{ padding: '0 4px', height: 22 }}
                        />
                      )}
                      <Popconfirm title={t('god.confirmDelete')} onConfirm={() => handleDelete(task.hint)}>
                        <Button
                          size="small"
                          type="text"
                          danger
                          icon={<DeleteOutlined style={{ fontSize: 11 }} />}
                          title="删除"
                          style={{ padding: '0 4px', height: 22 }}
                        />
                      </Popconfirm>
                    </Space>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <Text type="secondary" style={{ fontSize: 11, textAlign: 'center', display: 'block', marginTop: 6, flexShrink: 0 }}>
        {selectedNPC ? t('god.moveHelp') : t('god.selectNPC')}
      </Text>
    </div>
  );
}
