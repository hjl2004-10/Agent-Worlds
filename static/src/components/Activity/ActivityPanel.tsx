import { useEffect, useRef, useState } from 'react';
import { Divider } from 'antd';
import {
  MessageOutlined,
  SwapOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
  CarryOutOutlined,
  DownOutlined,
  UpOutlined,
} from '@ant-design/icons';
import { useActivityStore } from '@/store/useActivityStore';
import { usePolling } from '@/hooks/usePolling';
import { taskApi } from '@/api';
import { PixelBanner } from '@/components/ui';

const COLORS = ['#4ade80', '#38bdf8', '#e879f9', '#fbbf24', '#f87171'];

function getNPCColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  conversation_start: <MessageOutlined />,
  conversation_end: <SwapOutlined />,
  task_done: <CheckCircleOutlined />,
  move: <EnvironmentOutlined />,
  system: <ThunderboltOutlined />,
};

const EVENT_COLORS: Record<string, string> = {
  conversation_start: '#38bdf8',
  conversation_end: '#8a9a8a',
  task_done: '#4ade80',
  move: '#fbbf24',
  system: '#e879f9',
};

interface TaskItem {
  hint: string;
  source: string;
  tool_hint?: string;
  status: string;
}

export function ActivityPanel() {
  const { events, fetch } = useActivityStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [allTasks, setAllTasks] = useState<Record<string, TaskItem[]>>({});
  const [tasksExpanded, setTasksExpanded] = useState(true);

  usePolling(fetch, 3000);

  useEffect(() => {
    fetch();
    loadTasks();
  }, [fetch]);

  // 轮询任务
  usePolling(loadTasks, 5000);

  async function loadTasks() {
    try {
      const { data } = await taskApi.getAll();
      if (data.status === 'ok') {
        setAllTasks(data.pool);
      }
    } catch (err) {
      console.error('Load tasks failed:', err);
    }
  }

  // 收集待办和已完成任务
  const pendingTasks: { npc: string; task: TaskItem }[] = [];
  const doneTasks: { npc: string; task: TaskItem }[] = [];
  Object.entries(allTasks).forEach(([npc, tasks]) => {
    tasks.forEach((task) => {
      if (task.status === 'done') {
        doneTasks.push({ npc, task });
      } else {
        pendingTasks.push({ npc, task });
      }
    });
  });

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 标题 */}
      <div style={{ marginBottom: 8 }}>
        <PixelBanner variant="style3" style={{ height: 32 }}>
          <span style={{ fontSize: 13 }}>动态</span>
        </PixelBanner>
      </div>

      {/* 任务区域 */}
      <div style={{ marginBottom: 8 }}>
        <div
          onClick={() => setTasksExpanded(!tasksExpanded)}
          style={{
            cursor: 'pointer',
            padding: '5px 8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 12,
            color: 'var(--text-secondary)',
            background: 'var(--bg-hover-subtle)',
            borderTop: '1px solid var(--bg-hover)',
            borderBottom: '1px solid var(--bg-hover)',
            userSelect: 'none',
          }}
        >
          <span>
            <CarryOutOutlined style={{ marginRight: 4 }} />
            待办任务 ({pendingTasks.length})
          </span>
          {tasksExpanded ? <UpOutlined style={{ fontSize: 10 }} /> : <DownOutlined style={{ fontSize: 10 }} />}
        </div>

        {tasksExpanded && (
          <div style={{ maxHeight: 180, overflowY: 'auto', padding: '4px 0' }}>
            {pendingTasks.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '12px 0', color: 'var(--text-muted)', fontSize: 11 }}>
                暂无待办
              </div>
            ) : (
              pendingTasks.map((item, idx) => {
                const color = getNPCColor(item.npc);
                return (
                  <div
                    key={`${item.npc}-${idx}`}
                    style={{
                      padding: '5px 8px',
                      borderBottom: '1px solid var(--bg-hover)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 6,
                    }}
                  >
                    <ClockCircleOutlined style={{ color: '#fbbf24', fontSize: 11, marginTop: 2 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                        <span style={{ color, fontWeight: 600 }}>{item.npc}</span>
                        <span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>·</span>
                        <span>{item.task.hint}</span>
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>
                        来源: {item.task.source}
                        {item.task.tool_hint && ` · 工具: ${item.task.tool_hint.split(':')[0]}`}
                      </div>
                    </div>
                  </div>
                );
              })
            )}

            {/* 已完成折叠 */}
            {doneTasks.length > 0 && (
              <>
                <Divider style={{ margin: '6px 0', fontSize: 10 }}>
                  <span style={{ color: 'var(--text-muted)' }}>已完成 ({doneTasks.length})</span>
                </Divider>
                {doneTasks.map((item, idx) => {
                  const color = getNPCColor(item.npc);
                  return (
                    <div
                      key={`done-${item.npc}-${idx}`}
                      style={{
                        padding: '4px 8px',
                        opacity: 0.5,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        fontSize: 11,
                      }}
                    >
                      <CheckCircleOutlined style={{ color: '#4ade80', fontSize: 10 }} />
                      <span style={{ color, fontWeight: 600 }}>{item.npc}</span>
                      <span style={{ color: 'var(--text-muted)', textDecoration: 'line-through' }}>{item.task.hint}</span>
                    </div>
                  );
                })}
              </>
            )}
          </div>
        )}
      </div>

      {/* 事件时间线 */}
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '2px 8px', marginBottom: 4 }}>
        <ThunderboltOutlined style={{ marginRight: 4 }} />
        事件流
      </div>

      <div
        ref={scrollRef}
        className="memory-chat-area"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '6px 4px',
          minHeight: 100,
        }}
      >
        {events.length === 0 ? (
          <div className="empty-state-text">
            ··· 暂无动态 ···
          </div>
        ) : (
          events.map((evt, idx) => {
            const color = getNPCColor(evt.npc);
            const iconColor = EVENT_COLORS[evt.type] || '#8a9a8a';

            return (
              <div
                key={`${evt.tick}-${idx}`}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  padding: '5px 6px',
                  borderBottom: '1px solid var(--bg-hover)',
                  animation: idx === 0 ? 'panelFadeIn 0.3s ease-out' : undefined,
                }}
              >
                <div style={{
                  color: iconColor,
                  fontSize: 12,
                  marginTop: 2,
                  flexShrink: 0,
                  width: 14,
                  textAlign: 'center',
                }}>
                  {EVENT_ICONS[evt.type] || <ThunderboltOutlined />}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                    {evt.npc && (
                      <span style={{ color, fontWeight: 600, marginRight: 4 }}>
                        {evt.npc}
                      </span>
                    )}
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {evt.detail.replace(evt.npc, '').trim() || evt.detail}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>
                    {evt.date} {evt.time}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
