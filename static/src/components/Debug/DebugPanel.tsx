/**
 * DebugPanel - 调试浮窗 (Tabs: 对话调试 / 知识图谱)
 *
 * 对话调试: 左侧 LLM 调用列表, 右侧详情 (请求 messages / 返回 / 工具调用)
 * 知识图谱: 力导向图可视化关系网 (GraphView)
 */
import { useState, useEffect } from 'react';
import { Modal, Tabs, Input, Button, Tag, Typography, Space, Empty, Spin } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { debugApi } from '@/api/god';
import { GraphView } from '@/components/Debug/GraphView';
import { PendingManager } from '@/components/Debug/PendingManager';
import { ConfigPanel } from '@/components/Debug/ConfigPanel';

const { Text } = Typography;

interface LogSummary {
  id: number; ts: number; speaker: string; listener: string | null;
  conv_type: string; channel: string; model: string;
  message_count: number; tool_count: number; response_preview: string;
}

interface LogDetail {
  id: number; ts: number; speaker: string; listener: string | null;
  conv_type: string; channel: string; model: string;
  messages: { role: string; content: unknown }[];
  response: string;
  tool_calls: { name: string; input: Record<string, unknown> }[];
}

interface DebugPanelProps {
  open: boolean;
  onClose: () => void;
}

function fmtTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString('zh-CN', { hour12: false });
}

function roleColor(role: string): string {
  return ({ system: 'purple', user: 'blue', assistant: 'green' } as Record<string, string>)[role] || 'default';
}

function contentToStr(c: unknown): string {
  if (typeof c === 'string') return c;
  try { return JSON.stringify(c, null, 2); } catch { return String(c); }
}

export function DebugPanel({ open, onClose }: DebugPanelProps) {
  const [logs, setLogs] = useState<LogSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<LogDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [npcFilter, setNpcFilter] = useState('');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const { data } = await debugApi.getLLMLogs(npcFilter.trim() || undefined, 100);
      if (data.status === 'ok') setLogs(data.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, npcFilter]);

  const selectLog = async (id: number) => {
    setSelectedId(id);
    setDetail(null);
    const { data } = await debugApi.getLLMLog(id);
    if (data.status === 'ok') setDetail(data.entry as LogDetail);
  };

  const convView = (
    <div>
      <Space style={{ marginBottom: 8 }}>
        <Input.Search
          placeholder="按 NPC 过滤 (speaker/listener)"
          value={npcFilter}
          onChange={(e) => setNpcFilter(e.target.value)}
          style={{ width: 240 }}
          allowClear
        />
        <Button size="small" icon={<ReloadOutlined />} onClick={fetchLogs} loading={loading}>刷新</Button>
        <Text type="secondary">共 {logs.length} 条</Text>
      </Space>

      <div style={{ display: 'flex', gap: 8, height: '64vh' }}>
        {/* 左侧列表 */}
        <div style={{ width: '33%', overflowY: 'auto', borderRight: '1px solid #333', paddingRight: 8 }}>
          {loading && logs.length === 0 && <Spin />}
          {!loading && logs.length === 0 && <Empty description="暂无记录" />}
          {logs.map((l) => (
            <div
              key={l.id}
              onClick={() => selectLog(l.id)}
              style={{
                padding: '6px 8px', cursor: 'pointer', borderRadius: 4,
                background: selectedId === l.id ? '#1677ff33' : 'transparent',
                borderBottom: '1px solid #222',
              }}
            >
              <div>
                <Tag color="orange">{l.speaker}</Tag>
                <span style={{ color: '#888' }}>→</span>
                <Tag>{l.listener || '-'}</Tag>
                {l.tool_count > 0 && <Tag color="red">工具{l.tool_count}</Tag>}
              </div>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {fmtTime(l.ts)} · {l.channel} · {l.message_count}msg
              </Text>
              <div style={{ fontSize: 12, color: '#bbb', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {l.response_preview || '(空回复)'}
              </div>
            </div>
          ))}
        </div>

        {/* 右侧详情 */}
        <div style={{ flex: 1, overflowY: 'auto', paddingLeft: 8 }}>
          {!detail ? (
            <Empty description="选择左侧一条记录查看详情" />
          ) : (
            <div>
              <div style={{ marginBottom: 8 }}>
                <Tag color="orange">{detail.speaker}</Tag>
                <span style={{ color: '#888' }}>→</span>
                <Tag>{detail.listener || '-'}</Tag>
                <Tag>{detail.conv_type}</Tag>
                <Tag>{detail.channel}/{detail.model}</Tag>
              </div>

              <Text strong>请求 messages（{detail.messages.length}）</Text>
              <div style={{ marginBottom: 12 }}>
                {detail.messages.map((m, i) => (
                  <div key={i} style={{ marginBottom: 6, padding: 6, background: '#222', borderRadius: 4 }}>
                    <Tag color={roleColor(m.role)}>{m.role}</Tag>
                    <div style={{ fontSize: 12, whiteSpace: 'pre-wrap', color: '#ddd', maxHeight: 220, overflowY: 'auto' }}>
                      {contentToStr(m.content)}
                    </div>
                  </div>
                ))}
              </div>

              <Text strong>返回</Text>
              <div style={{ marginBottom: 12, padding: 6, background: '#0d2b0d', borderRadius: 4, whiteSpace: 'pre-wrap', color: '#bfb' }}>
                {detail.response || '(空)'}
              </div>

              {detail.tool_calls.length > 0 && (
                <>
                  <Text strong>工具调用（{detail.tool_calls.length}）</Text>
                  <div>
                    {detail.tool_calls.map((t, i) => (
                      <div key={i} style={{ padding: 6, background: '#2b1d0d', borderRadius: 4, marginBottom: 4 }}>
                        <Tag color="red">{t.name}</Tag>
                        <code style={{ fontSize: 11, color: '#fdb' }}>{JSON.stringify(t.input)}</code>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <Modal
      title="调试面板"
      open={open}
      onCancel={onClose}
      footer={null}
      width="95%"
      styles={{ body: { background: 'var(--bg-panel, #1a1a1a)' } }}
      style={{ top: 20 }}
    >
      <Tabs
        defaultActiveKey="conv"
        items={[
          { key: 'conv', label: '对话调试', children: convView },
          { key: 'graph', label: '知识图谱', children: <GraphView /> },
          { key: 'manage', label: '管理', children: <PendingManager /> },
          { key: 'config', label: '配置', children: <ConfigPanel /> },
        ]}
      />
    </Modal>
  );
}
