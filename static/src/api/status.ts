import client from './client';
import type { StatusResponse, EventResponse } from './types';

export const statusApi = {
  getStatus: () => client.get<StatusResponse>('/status'),

  getEvent: () => client.get<EventResponse>('/event'),
};
