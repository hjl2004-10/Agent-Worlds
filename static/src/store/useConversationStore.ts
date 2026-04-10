import { create } from 'zustand';
import { conversationApi } from '@/api';
import type { ConversationState } from '@/api/types';

interface ConversationStore extends ConversationState {
  fetchState: () => Promise<void>;
  sendInput: (playerName: string, text: string) => Promise<boolean>;
  endConversation: () => Promise<void>;
}

export const useConversationStore = create<ConversationStore>((set) => ({
  active: false,
  speaker: null,
  listener: null,
  waiting: false,
  is_player_conversation: false,

  fetchState: async () => {
    try {
      const { data } = await conversationApi.getState();
      set({
        active: data.active,
        speaker: data.speaker,
        listener: data.listener,
        waiting: data.waiting,
        is_player_conversation: data.is_player_conversation ?? false,
      });
    } catch (err) {
      console.error('Fetch conversation state failed:', err);
    }
  },

  sendInput: async (playerName: string, text: string) => {
    try {
      const { data } = await conversationApi.sendInput({
        player_name: playerName,
        text,
      });
      return data.status === 'ok';
    } catch {
      return false;
    }
  },

  endConversation: async () => {
    try {
      await conversationApi.end();
      set({ active: false, speaker: null, listener: null, waiting: false });
    } catch (err) {
      console.error('End conversation failed:', err);
    }
  },
}));
