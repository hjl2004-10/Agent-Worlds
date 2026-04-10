import client from './client';

export interface ActivityEvent {
  tick: number;
  time: string;
  date: string;
  type: string;
  npc: string;
  detail: string;
}

interface EventsResponse {
  status: string;
  events: ActivityEvent[];
}

export const activityApi = {
  getEvents: (limit = 50) => client.get<EventsResponse>(`/events?limit=${limit}`),
};
