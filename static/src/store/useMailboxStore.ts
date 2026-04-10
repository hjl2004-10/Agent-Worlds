/**
 * useMailboxStore - 邮箱状态管理
 *
 * 仿照 useNPCStore / useStatusStore 的风格重构
 * 直接使用 API 返回数据，不依赖 status 字段判断
 */
import { create } from 'zustand';
import { mailboxApi } from '@/api';
import type { Mail } from '@/api';

interface MailboxStore {
  // 状态
  mails: Mail[];
  unreadCount: number;
  loading: boolean;
  error: string | null;
  selectedMail: Mail | null;
  modalOpen: boolean;

  // 操作
  fetchInbox: (playerName?: string) => Promise<void>;
  fetchUnreadCount: (playerName?: string) => Promise<void>;
  markAsRead: (mailId: string, playerName?: string) => Promise<boolean>;
  markAllAsRead: (playerName?: string) => Promise<number>;
  deleteMail: (mailId: string, playerName?: string) => Promise<boolean>;
  toggleStar: (mailId: string, playerName?: string) => Promise<boolean>;
  selectMail: (mail: Mail | null) => void;
  openModal: () => void;
  closeModal: () => void;
}

export const useMailboxStore = create<MailboxStore>((set) => ({
  mails: [],
  unreadCount: 0,
  loading: false,
  error: null,
  selectedMail: null,
  modalOpen: false,

  fetchInbox: async (playerName = 'player') => {
    set({ loading: true, error: null });
    try {
      const { data } = await mailboxApi.getInbox(playerName);
      set({
        mails: data.mails || [],
        unreadCount: data.unread_count || 0,
      });
    } catch (err) {
      console.error('Fetch inbox failed:', err);
      set({ error: '获取邮箱失败' });
    } finally {
      set({ loading: false });
    }
  },

  fetchUnreadCount: async (playerName = 'player') => {
    try {
      const { data } = await mailboxApi.getUnreadCount(playerName);
      set({ unreadCount: data.unread_count || 0 });
    } catch (err) {
      console.error('Fetch unread count failed:', err);
    }
  },

  markAsRead: async (mailId: string, playerName = 'player') => {
    try {
      await mailboxApi.markAsRead(playerName, mailId);
      set((state) => {
        const mail = state.mails.find((m) => m.id === mailId);
        const wasUnread = mail && !mail.read;
        return {
          mails: state.mails.map((m) =>
            m.id === mailId
              ? { ...m, read: true, read_at: new Date().toISOString() }
              : m
          ),
          unreadCount: wasUnread
            ? Math.max(0, state.unreadCount - 1)
            : state.unreadCount,
        };
      });
      return true;
    } catch (err) {
      console.error('Mark as read failed:', err);
      return false;
    }
  },

  markAllAsRead: async (playerName = 'player') => {
    try {
      const { data } = await mailboxApi.markAllAsRead(playerName);
      const count = data.count || 0;
      set((state) => ({
        mails: state.mails.map((mail) => ({
          ...mail,
          read: true,
          read_at: mail.read_at || new Date().toISOString(),
        })),
        unreadCount: 0,
      }));
      return count;
    } catch (err) {
      console.error('Mark all as read failed:', err);
      return 0;
    }
  },

  deleteMail: async (mailId: string, playerName = 'player') => {
    try {
      await mailboxApi.deleteMail(playerName, mailId);
      set((state) => {
        const mail = state.mails.find((m) => m.id === mailId);
        const wasUnread = mail && !mail.read;
        return {
          mails: state.mails.filter((m) => m.id !== mailId),
          unreadCount: wasUnread
            ? Math.max(0, state.unreadCount - 1)
            : state.unreadCount,
          selectedMail: state.selectedMail?.id === mailId ? null : state.selectedMail,
        };
      });
      return true;
    } catch (err) {
      console.error('Delete mail failed:', err);
      return false;
    }
  },

  toggleStar: async (mailId: string, playerName = 'player') => {
    try {
      const { data } = await mailboxApi.toggleStar(playerName, mailId);
      const newStarred = data.starred ?? false;
      set((state) => ({
        mails: state.mails.map((mail) =>
          mail.id === mailId ? { ...mail, starred: newStarred } : mail
        ),
        selectedMail:
          state.selectedMail?.id === mailId
            ? { ...state.selectedMail, starred: newStarred }
            : state.selectedMail,
      }));
      return newStarred;
    } catch (err) {
      console.error('Toggle star failed:', err);
      return false;
    }
  },

  selectMail: (mail: Mail | null) => {
    set({ selectedMail: mail });
  },

  openModal: () => {
    set({ modalOpen: true });
  },

  closeModal: () => {
    set({ modalOpen: false, selectedMail: null });
  },
}));
