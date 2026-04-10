import client from './client';

// ========== Types ==========

export interface Mail {
  id: string;
  from: string;
  to: string;
  title: string;
  content: string;
  content_type: 'text' | 'html' | 'image' | 'document' | 'html_app';
  read: boolean;
  starred: boolean;
  created_at: string;
  read_at: string | null;
  metadata?: {
    image_url?: string;
    local_path?: string;
    doc_format?: string;
    description?: string;
    device_mode?: 'mobile' | 'desktop';
    viewport?: { width: number; height: number };
    icon?: string;
  };
}

export interface MailboxResponse {
  status: string;
  mails: Mail[];
  unread_count: number;
}

export interface UnreadResponse {
  status: string;
  unread_count: number;
}

export interface ActionResponse {
  status: string;
  message?: string;
  count?: number;
  starred?: boolean;
}

// ========== API ==========

export const mailboxApi = {
  /**
   * 获取收件箱
   */
  getInbox: (playerName: string = 'player') =>
    client.get<MailboxResponse>(`/mailbox/${encodeURIComponent(playerName)}`),

  /**
   * 获取未读数量
   */
  getUnreadCount: (playerName: string = 'player') =>
    client.get<UnreadResponse>(`/mailbox/${encodeURIComponent(playerName)}/unread`),

  /**
   * 标记邮件为已读
   */
  markAsRead: (playerName: string, mailId: string) =>
    client.post<ActionResponse>(`/mailbox/${encodeURIComponent(playerName)}/read/${mailId}`),

  /**
   * 标记所有邮件为已读
   */
  markAllAsRead: (playerName: string = 'player') =>
    client.post<ActionResponse>(`/mailbox/${encodeURIComponent(playerName)}/read-all`),

  /**
   * 删除邮件
   */
  deleteMail: (playerName: string, mailId: string) =>
    client.delete<ActionResponse>(`/mailbox/${encodeURIComponent(playerName)}/${mailId}`),

  /**
   * 切换星标
   */
  toggleStar: (playerName: string, mailId: string) =>
    client.post<ActionResponse>(`/mailbox/${encodeURIComponent(playerName)}/star/${mailId}`),

  /**
   * 获取文件 URL
   * 使用环境变量中的 API 地址，确保生产环境下指向正确的后端
   */
  getFileUrl: (path: string) => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
    return `${baseUrl}/mailbox/file?path=${encodeURIComponent(path)}`;
  },
};
