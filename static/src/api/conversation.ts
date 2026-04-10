import client from './client';
import type {
  ConversationState,
  PlayerInputRequest,
  PlayerInputResponse
} from './types';

export const conversationApi = {
  getState: () => client.get<ConversationState>('/conversation/state'),

  end: () => client.post<{ status: string }>('/conversation/end'),

  sendInput: (data: PlayerInputRequest) =>
    client.post<PlayerInputResponse>('/player/input', data),
};
