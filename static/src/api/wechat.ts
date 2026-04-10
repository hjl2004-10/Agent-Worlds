import client from './client';

export interface WechatBindResponse {
  status?: string;
  qrcode_url?: string;
  session_key?: string;
  error?: string;
}

export interface WechatStatusResponse {
  status: 'unbound' | 'qr_pending' | 'bound';
  ilink_bot_id?: string;
}

export interface WechatBindingsResponse {
  status: string;
  bindings: Record<string, { status: string; ilink_bot_id: string }>;
}

export const wechatApi = {
  /** 发起绑定 (获取二维码) */
  bind: (npcName: string) =>
    client.post<WechatBindResponse>('/wechat/bind', { npc_name: npcName }),

  /** 解除绑定 */
  unbind: (npcName: string) =>
    client.post<WechatStatusResponse>('/wechat/unbind', { npc_name: npcName }),

  /** 查询绑定状态 */
  getStatus: (npcName: string) =>
    client.get<WechatStatusResponse>(`/wechat/status/${encodeURIComponent(npcName)}`),

  /** 获取所有绑定 */
  getAllBindings: () =>
    client.get<WechatBindingsResponse>('/wechat/bindings'),

  /** 手动发送消息 (调试) */
  send: (npcName: string, text: string) =>
    client.post('/wechat/send', { npc_name: npcName, text }),
};
