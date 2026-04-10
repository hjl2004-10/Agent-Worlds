import { useState, useEffect, useRef } from 'react';
import { Space, Typography, Tag } from 'antd';
import { SendOutlined, StopOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useConversationStore } from '@/store/useConversationStore';
import { useNPCStore } from '@/store/useNPCStore';
import { godApi } from '@/api';
import { PixelBanner, PixelButton } from '@/components/ui';
import type { MemoryItem } from '@/api/types';

const { Text } = Typography;

const POLL_INTERVAL = 3000;

const COLORS = ['#4ade80', '#38bdf8', '#e879f9', '#fbbf24', '#f87171'];

function getNPCColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

interface ParsedMessage {
  speaker: string;
  content: string;
  isRight: boolean;
  source?: string;  // 'wechat' | undefined
}

/**
 * 解析 ram_buffer 条目
 * npcName: 被观察的 NPC (assistant = 自己说的)
 * partnerName: 对话对象 (user = 对方说的)
 */
function parseMemoryItem(
  item: MemoryItem,
  npcName: string,
  partnerName: string,
): ParsedMessage | null {
  if (typeof item === 'object') {
    const isSelf = item.role === 'assistant';
    return {
      speaker: isSelf ? npcName : (item.source === 'wechat' ? '微信用户' : partnerName),
      content: item.content,
      isRight: isSelf,
      source: item.source,
    };
  }
  return null;
}

export function PlayerInput() {
  const {
    active,
    speaker,
    listener,
    waiting,
    is_player_conversation,
    sendInput,
    endConversation,
  } = useConversationStore();

  const { npcs } = useNPCStore();

  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);

  const [talkingNPCs, setTalkingNPCs] = useState<string[]>([]);
  const [messages, setMessages] = useState<ParsedMessage[]>([]);
  const [partnerName, setPartnerName] = useState<string>('');
  const [lastCount, setLastCount] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const talking = npcs.filter(n => n.is_talking).map(n => n.name);
    setTalkingNPCs(talking);
  }, [npcs]);

  useEffect(() => {
    if (talkingNPCs.length === 0) {
      setMessages([]);
      setPartnerName('');
      setLastCount(0);
      return;
    }

    const primaryNPC = talkingNPCs[0];

    const poll = async () => {
      try {
        const { data } = await godApi.getRamBuffer(primaryNPC);
        if (data.status === 'ok' && data.items) {
          const partner = data.partner || (
            talkingNPCs.length >= 2 ? talkingNPCs[1] : '对方'
          );
          setPartnerName(partner);

          const parsed = data.items
            .map(item => parseMemoryItem(item, primaryNPC, partner))
            .filter((m): m is ParsedMessage => m !== null);

          if (parsed.length !== lastCount) {
            setMessages(parsed);
            setLastCount(parsed.length);

            if (scrollRef.current) {
              setTimeout(() => {
                if (scrollRef.current) {
                  scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                }
              }, 0);
            }
          }
        }
      } catch (err) {
        console.error(`Poll ${primaryNPC} failed:`, err);
      }
    };

    poll();
    const id = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [talkingNPCs, lastCount]);

  const handleSend = async () => {
    if (!inputText.trim() || !waiting || !speaker) return;

    setSending(true);
    const success = await sendInput(speaker, inputText.trim());
    if (success) {
      setInputText('');
    }
    setSending(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getStatusTag = () => {
    if (talkingNPCs.length > 0) {
      return <Tag color="processing" style={{ fontSize: 10 }}>对话中</Tag>;
    }
    return <Tag color="default" style={{ fontSize: 10 }}>空闲</Tag>;
  };

  const canInput = active && is_player_conversation;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 标题栏 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <PixelBanner variant="style2" style={{ height: 32 }}>
          <Space size={6}>
            <span style={{ fontSize: 13 }}>实时对话</span>
          </Space>
        </PixelBanner>
        {getStatusTag()}
        {talkingNPCs.length > 0 && partnerName && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {talkingNPCs[0]} ↔ {partnerName}
          </Text>
        )}
      </div>

      {/* 实时对话显示区 */}
      <div
        ref={scrollRef}
        className="memory-chat-area"
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          padding: '10px 8px',
          marginBottom: 8,
          minHeight: 200,
        }}
      >
        {messages.length === 0 ? (
          <div className="empty-state-text">
            ···  暂无对话  ···
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                justifyContent: msg.isRight ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  maxWidth: '85%',
                  display: 'flex',
                  flexDirection: msg.isRight ? 'row-reverse' : 'row',
                  alignItems: 'flex-start',
                  gap: 6,
                }}
              >
                {/* 名字标签 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                  {msg.source === 'wechat' && (
                    <span style={{
                      fontSize: 9,
                      background: '#07c160',
                      color: '#fff',
                      borderRadius: 3,
                      padding: '1px 4px',
                      lineHeight: 1.3,
                    }}>微信</span>
                  )}
                  <div
                    className="msg-speaker-tag"
                    style={{
                      background: `${getNPCColor(msg.speaker)}22`,
                      color: getNPCColor(msg.speaker),
                    }}
                  >
                    {msg.speaker}
                  </div>
                </div>

                {/* 像素气泡 + Markdown */}
                <div className={`pixel-bubble pixel-bubble--${msg.isRight ? 'right' : 'left'}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 玩家输入区 — 仅玩家参与的对话才显示 */}
      {canInput ? (
        <>
          <div style={{ marginBottom: 8, fontSize: 12 }}>
            <Text strong style={{ color: 'var(--text-primary)' }}>{speaker}</Text>
            <Text type="secondary"> ↔ </Text>
            <Text strong style={{ color: 'var(--text-primary)' }}>{listener}</Text>
          </div>

          <input
            className="pixel-input"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={waiting ? '输入对话...' : '等待响应...'}
            disabled={!waiting}
          />

          <Space style={{ marginTop: 8, width: '100%', justifyContent: 'flex-end' }}>
            <PixelButton
              variant="style1"
              size="sm"
              onClick={endConversation}
            >
              <StopOutlined /> 结束
            </PixelButton>
            <PixelButton
              variant="style2"
              size="sm"
              onClick={handleSend}
              disabled={sending || !waiting || !inputText.trim()}
            >
              <SendOutlined /> 发送
            </PixelButton>
          </Space>
        </>
      ) : active ? (
        <Text type="secondary" className="cursor-blink" style={{ fontSize: 11, textAlign: 'center' }}>
          NPC 对话中，仅观察
        </Text>
      ) : (
        <Text type="secondary" style={{ fontSize: 11, textAlign: 'center' }}>
          无对话进行中
        </Text>
      )}
    </div>
  );
}
