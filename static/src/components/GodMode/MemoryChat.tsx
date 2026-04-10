import { useState, useEffect, useRef, useCallback } from 'react';
import { Typography, Spin, Divider } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { godApi } from '@/api';
import type { MemoryItem } from '@/api/types';

const { Text } = Typography;

// NPC 颜色映射 (和 NPCList 保持一致)
const COLORS = ['#4ade80', '#38bdf8', '#e879f9', '#fbbf24', '#f87171'];

// 获取 NPC 对应的颜色
function getNPCColor(name: string, allNPCs: string[] = []): string {
  const index = allNPCs.indexOf(name);
  if (index >= 0) return COLORS[index % COLORS.length];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

interface MemoryChatProps {
  npcName: string;
  allNPCNames?: string[];
  refreshKey?: number;
}

interface ParsedMessage {
  type: 'said' | 'heard' | 'raw';
  speaker: string;
  listener: string;
  content: string;
  time?: string;
  isSelf: boolean;
}

// 解析记忆条目
function parseMemoryItem(item: MemoryItem, selfName: string): ParsedMessage | null {
  if (typeof item === 'object') {
    const isSelf = item.role === 'assistant';
    return {
      type: 'raw',
      speaker: isSelf ? selfName : 'Player',
      listener: isSelf ? 'Player' : selfName,
      content: item.content,
      isSelf,
    };
  }

  const saidMatch = item.match(/^\[([^\]]+)\]\s*我对(\S+)说:\s*(.+)$/s);
  if (saidMatch) {
    return {
      type: 'said',
      speaker: selfName,
      listener: saidMatch[2],
      content: saidMatch[3],
      time: saidMatch[1],
      isSelf: true,
    };
  }

  const heardMatch = item.match(/^\[([^\]]+)\]\s*(\S+)对我说:\s*(.+)$/s);
  if (heardMatch) {
    return {
      type: 'heard',
      speaker: heardMatch[2],
      listener: selfName,
      content: heardMatch[3],
      time: heardMatch[1],
      isSelf: false,
    };
  }

  return null;
}

export function MemoryChat({ npcName, allNPCNames = [], refreshKey = 0 }: MemoryChatProps) {
  const [messages, setMessages] = useState<ParsedMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [loadedCount, setLoadedCount] = useState(0);
  const [total, setTotal] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevScrollHeightRef = useRef(0);
  const PAGE_SIZE = 10;
  const RECENT_THRESHOLD = 5;

  // 加载历史记忆
  useEffect(() => {
    setMessages([]);
    setLoadedCount(0);
    setHasMore(true);
    setTotal(0);

    const load = async () => {
      setLoading(true);
      try {
        const { data } = await godApi.getMemory(npcName, 0, 1000);
        if (data.status === 'ok' && data.items) {
          const allParsed = data.items
            .map((item: MemoryItem) => parseMemoryItem(item, npcName))
            .filter((m): m is ParsedMessage => m !== null);

          setTotal(allParsed.length);
          const initialMessages = allParsed.slice(-PAGE_SIZE);
          setMessages(initialMessages);
          setLoadedCount(initialMessages.length);
          setHasMore(allParsed.length > PAGE_SIZE);
        }
      } catch (err) {
        console.error('Load memory failed:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [npcName, refreshKey]);

  // 初始加载后滚动到底部
  useEffect(() => {
    if (messages.length > 0 && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length > 0 && loadedCount === PAGE_SIZE]);

  // 加载更多后保持滚动位置
  useEffect(() => {
    if (loading === false && prevScrollHeightRef.current > 0 && scrollRef.current) {
      const newScrollHeight = scrollRef.current.scrollHeight;
      scrollRef.current.scrollTop = newScrollHeight - prevScrollHeightRef.current;
      prevScrollHeightRef.current = 0;
    }
  }, [loading, messages.length]);

  // 滚动加载更多
  const handleScroll = useCallback(() => {
    const container = scrollRef.current;
    if (!container || loading || !hasMore) return;

    if (container.scrollTop < 50) {
      const end = total - loadedCount;
      const start = Math.max(0, end - PAGE_SIZE);
      if (start < end) {
        prevScrollHeightRef.current = container.scrollHeight;
        setLoading(true);

        godApi.getMemory(npcName, 0, 1000).then(({ data }) => {
          if (data.status === 'ok' && data.items) {
            const allParsed = data.items
              .map((item: MemoryItem) => parseMemoryItem(item, npcName))
              .filter((m): m is ParsedMessage => m !== null);

            const oldMessages = allParsed.slice(start, end);
            setMessages(prev => [...oldMessages, ...prev]);
            setLoadedCount(prev => prev + oldMessages.length);
            setHasMore(start > 0);
          }
        }).catch(err => {
          console.error('Load more failed:', err);
        }).finally(() => {
          setLoading(false);
        });
      }
    }
  }, [loading, hasMore, total, loadedCount, npcName]);

  const separatorIndex = messages.length - RECENT_THRESHOLD;

  if (messages.length === 0 && !loading) {
    return (
      <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)' }}>
        暂无历史记忆
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="memory-chat-area"
      style={{
        height: 375,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        padding: '10px 8px',
      }}
    >
      {/* 加载更多提示 */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 8 }}>
          <Spin size="small" />
        </div>
      )}

      {!hasMore && messages.length > 0 && (
        <div style={{ textAlign: 'center', padding: 8, color: 'var(--text-muted)', fontSize: 11 }}>
          已加载全部 {total} 条历史记录
        </div>
      )}

      {/* 消息列表 */}
      {messages.map((msg, idx) => {
        const color = getNPCColor(msg.speaker, allNPCNames);
        const isRight = msg.isSelf;

        return (
          <div key={idx}>
            {/* 分隔线 */}
            {idx === separatorIndex && messages.length > RECENT_THRESHOLD && (
              <Divider style={{ margin: '8px 0', borderColor: '#3a3a5a' }}>
                <Text style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  最近 {RECENT_THRESHOLD} 条
                </Text>
              </Divider>
            )}

            <div
              style={{
                display: 'flex',
                justifyContent: isRight ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  maxWidth: '85%',
                  display: 'flex',
                  flexDirection: isRight ? 'row-reverse' : 'row',
                  alignItems: 'flex-start',
                  gap: 6,
                }}
              >
                {/* 名字标签 */}
                <div
                  className="msg-speaker-tag"
                  style={{
                    background: `${color}22`,
                    color: color,
                  }}
                >
                  {msg.speaker}
                </div>

                {/* 像素气泡 + Markdown */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <div className={`pixel-bubble pixel-bubble--${isRight ? 'right' : 'left'}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                  {msg.time && (
                    <div
                      className="msg-time"
                      style={{ textAlign: isRight ? 'right' : 'left' }}
                    >
                      {msg.time}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
