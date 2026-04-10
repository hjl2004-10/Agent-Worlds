import client from './client';
import type { NPC } from './types';

export const npcApi = {
  getAll: () => client.get<NPC[]>('/npcs'),

  getPlayers: () => client.get<NPC[]>('/players'),
};
