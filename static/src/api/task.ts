import client from './client';
import type {
  TaskAssignRequest,
  TaskAssignResponse,
  TaskListResponse,
  TaskActionResponse
} from './types';

export const taskApi = {
  assign: (data: TaskAssignRequest) =>
    client.post<TaskAssignResponse>('/tasks/assign', data),

  getAll: () =>
    client.get<{ status: string; pool: Record<string, { hint: string; source: string; tool_hint?: string; status: string }[]> }>('/tasks/all'),

  getList: (npcName: string) =>
    client.get<TaskListResponse>(`/tasks/${encodeURIComponent(npcName)}`),

  delete: (npcName: string, hint: string) =>
    client.delete<TaskActionResponse>(`/tasks/${encodeURIComponent(npcName)}`, {
      data: { hint },
    }),

  complete: (npcName: string, hint: string) =>
    client.patch<TaskActionResponse>(
      `/tasks/${encodeURIComponent(npcName)}/complete`,
      { hint }
    ),
};
