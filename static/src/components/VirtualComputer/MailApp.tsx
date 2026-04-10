/**
 * MailApp - 邮箱应用
 *
 * 显示普通邮件列表和详情
 */
import { useState } from 'react';
import { Tag, Button, Popconfirm } from 'antd';
import { StarOutlined, StarFilled, DeleteOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Mail } from '@/api';
import { mailboxApi } from '@/api';

interface MailAppProps {
  mails: Mail[];
  onBack: () => void;
  onSelectMail: (mail: Mail) => void;
  selectedMail: Mail | null;
  onMarkAllAsRead: () => void;
  onDeleteMail: (mailId: string) => void;
  onToggleStar: (mailId: string) => void;
}

// Markdown 样式
const markdownStyles = `
.mail-markdown h1 { font-size: 1.5em; margin: 0.5em 0; color: #fff; border-bottom: 1px solid #333; padding-bottom: 0.3em; }
.mail-markdown h2 { font-size: 1.3em; margin: 0.5em 0; color: #fff; }
.mail-markdown h3 { font-size: 1.1em; margin: 0.5em 0; color: #fff; }
.mail-markdown p { margin: 0.5em 0; line-height: 1.6; }
.mail-markdown ul, .mail-markdown ol { padding-left: 1.5em; margin: 0.5em 0; }
.mail-markdown li { margin: 0.25em 0; }
.mail-markdown code { background: rgba(255,255,255,0.1); padding: 0.1em 0.3em; border-radius: 3px; font-family: monospace; }
.mail-markdown pre { background: #1a1a1a; padding: 12px; border-radius: 6px; overflow-x: auto; }
.mail-markdown pre code { background: none; padding: 0; }
.mail-markdown blockquote { border-left: 3px solid #1890ff; padding-left: 12px; margin: 0.5em 0; color: #aaa; }
.mail-markdown a { color: #1890ff; text-decoration: none; }
.mail-markdown a:hover { text-decoration: underline; }
.mail-markdown table { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
.mail-markdown th, .mail-markdown td { border: 1px solid #333; padding: 8px; text-align: left; }
.mail-markdown th { background: #1a1a1a; }
.mail-markdown hr { border: none; border-top: 1px solid #333; margin: 1em 0; }
.mail-markdown img { max-width: 100%; border-radius: 6px; }
`;

export function MailApp({
  mails,
  onBack: _onBack,
  onSelectMail,
  selectedMail,
  onMarkAllAsRead,
  onDeleteMail,
  onToggleStar,
}: MailAppProps) {
  const [view, setView] = useState<'list' | 'detail'>('list');

  const formatTime = (timeStr: string) => {
    const date = new Date(timeStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'image':
        return '🖼️';
      case 'document':
        return '📄';
      default:
        return '📝';
    }
  };

  const handleSelectMail = (mail: Mail) => {
    onSelectMail(mail);
    setView('detail');
  };

  const handleBackToList = () => {
    setView('list');
  };

  // 邮件详情视图
  if (view === 'detail' && selectedMail) {
    return (
      <div className="mail-app">
        <div className="mail-detail">
          <div className="mail-detail-header" style={{ padding: '8px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Button
                type="text"
                icon={<ArrowLeftOutlined />}
                onClick={handleBackToList}
                size="small"
                style={{ color: 'var(--text-white)', padding: 0, flexShrink: 0 }}
              />
              <span style={{ color: 'var(--text-white)', fontWeight: 500, fontSize: 14, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {selectedMail.title}
              </span>
              <Tag color="blue" style={{ margin: 0, flexShrink: 0 }}>{getTypeIcon(selectedMail.content_type)} {selectedMail.content_type}</Tag>
            </div>
            <div style={{ marginTop: 2, paddingLeft: 28, display: 'flex', gap: 8, fontSize: 11 }}>
              <span style={{ color: 'var(--text-icon-muted)' }}>{selectedMail.from}</span>
              <span style={{ color: '#666' }}>{formatTime(selectedMail.created_at)}</span>
            </div>
          </div>

          <div className="mail-detail-content">
            {selectedMail.content_type === 'image' ? (
              <div style={{ textAlign: 'center' }}>
                <img
                  src={selectedMail.metadata?.image_url || mailboxApi.getFileUrl(selectedMail.content)}
                  alt={selectedMail.title}
                  style={{ maxWidth: '100%', borderRadius: 8 }}
                />
                {selectedMail.metadata?.description && (
                  <p style={{ marginTop: 12, color: 'var(--text-icon-muted)' }}>{selectedMail.metadata.description}</p>
                )}
              </div>
            ) : selectedMail.content_type === 'document' ? (
              <div style={{ textAlign: 'center', padding: 20 }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>📄</div>
                <p style={{ color: 'var(--text-white)', marginBottom: 8 }}>{selectedMail.title}</p>
                <p style={{ color: 'var(--text-icon-muted)', marginBottom: 16 }}>
                  格式: {selectedMail.metadata?.doc_format || 'TXT'}
                </p>
                <Button
                  type="primary"
                  href={mailboxApi.getFileUrl(selectedMail.content)}
                  target="_blank"
                >
                  打开文件
                </Button>
              </div>
            ) : (
              <div className="mail-markdown" style={{ fontSize: 14, lineHeight: 1.8 }}>
                <style>{markdownStyles}</style>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedMail.content}</ReactMarkdown>
              </div>
            )}
          </div>

          <div style={{ padding: '6px 12px', background: '#1a1a1a', borderTop: '1px solid #333', display: 'flex', gap: 8 }}>
            <Button
              size="small"
              icon={selectedMail.starred ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
              onClick={() => onToggleStar(selectedMail.id)}
            >
              {selectedMail.starred ? '取消星标' : '星标'}
            </Button>
            <Popconfirm
              title="确定删除？"
              onConfirm={() => {
                onDeleteMail(selectedMail.id);
                setView('list');
              }}
            >
              <Button size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </div>
        </div>
      </div>
    );
  }

  // 邮件列表视图
  return (
    <div className="mail-app">
      <div className="mail-app-header">
        <h2>📧 邮箱 ({mails.length})</h2>
        {mails.some((m) => !m.read) && (
          <Button size="small" onClick={onMarkAllAsRead}>
            全部已读
          </Button>
        )}
      </div>

      <div className="mail-list">
        {mails.length === 0 ? (
          <div className="empty-state">暂无邮件</div>
        ) : (
          mails.map((mail) => (
            <div
              key={mail.id}
              className={`mail-item ${!mail.read ? 'unread' : ''}`}
              onClick={() => handleSelectMail(mail)}
            >
              <div className="mail-item-header">
                <span style={{ fontSize: 16 }}>{getTypeIcon(mail.content_type)}</span>
                <span className="mail-item-title">{mail.title}</span>
                {mail.starred && <StarFilled style={{ color: '#faad14', fontSize: 12 }} />}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="mail-item-from">{mail.from}</span>
                <span className="mail-item-time">{formatTime(mail.created_at)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
