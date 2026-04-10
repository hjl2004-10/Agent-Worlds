import client from './client';
import type { ToolsResponse } from './types';

export const toolsApi = {
  getAll: () => client.get<ToolsResponse>('/tools'),
};
