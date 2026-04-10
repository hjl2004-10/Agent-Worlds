import { useEffect, useState } from 'react';
import { Tabs } from 'antd';
import {
  ThunderboltOutlined,
  MessageOutlined,
  UnorderedListOutlined,
  GlobalOutlined,
} from '@ant-design/icons';

import { AppLayout } from '@/components/Layout/AppLayout';
import { MapView } from '@/components/Map/MapView';
import { NPCList } from '@/components/NPC/NPCList';
import { GodControl } from '@/components/GodMode/GodControl';
import { PlayerInput } from '@/components/Player/PlayerInput';
import { ActivityPanel } from '@/components/Activity/ActivityPanel';
import { LorePanel } from '@/components/World/LorePanel';
import { MailboxIcon, MailboxModal } from '@/components/Mailbox';
import { FormIcon, FormModal } from '@/components/Form';
import { PixelPanel } from '@/components/ui';

import { usePolling } from '@/hooks/usePolling';
import { useThemeStore } from '@/store/useThemeStore';
import { useStatusStore } from '@/store/useStatusStore';
import { useNPCStore } from '@/store/useNPCStore';
import { useGodStore } from '@/store/useGodStore';
import { useConversationStore } from '@/store/useConversationStore';

function App() {
  const { init: initTheme } = useThemeStore();
  const { fetch: fetchStatus } = useStatusStore();
  const { fetch: fetchNPCs } = useNPCStore();
  const { fetchStatus: fetchGodStatus } = useGodStore();
  const { fetchState: fetchConversationState } = useConversationStore();

  const [activeTab, setActiveTab] = useState('command');

  // 轮询更新数据
  usePolling(() => {
    fetchStatus();
    fetchNPCs();
    fetchGodStatus();
    fetchConversationState();
  }, 500);

  // 初始化
  useEffect(() => {
    initTheme();
    fetchStatus();
    fetchNPCs();
    fetchGodStatus();
    fetchConversationState();
  }, [initTheme, fetchStatus, fetchNPCs, fetchGodStatus, fetchConversationState]);

  const { selectNPC } = useGodStore();

  const handleNPCClick = (name: string) => {
    selectNPC(name);
  };

  const tabItems = [
    {
      key: 'command',
      label: (
        <span>
          <ThunderboltOutlined />
          指挥
        </span>
      ),
      children: <GodControl />,
    },
    {
      key: 'player',
      label: (
        <span>
          <MessageOutlined />
          对话
        </span>
      ),
      children: <PlayerInput />,
    },
    {
      key: 'activity',
      label: (
        <span>
          <UnorderedListOutlined />
          动态
        </span>
      ),
      children: <ActivityPanel />,
    },
    {
      key: 'lore',
      label: (
        <span>
          <GlobalOutlined />
          世界
        </span>
      ),
      children: <LorePanel />,
    },
  ];

  // 侧边栏宽度
  const SIDEBAR_WIDTH = 420;

  return (
    <AppLayout>
      {/* 主内容区 */}
      <div style={{ display: 'flex', height: 'calc(100vh - 82px)', gap: 12 }}>
        {/* NPC 列表 - 左侧 */}
        <PixelPanel variant="gray" style={{ width: 220, flexShrink: 0, overflow: 'hidden', animationDelay: '0.05s' }}>
          <NPCList onNPCClick={handleNPCClick} />
        </PixelPanel>

        {/* 地图区域 - 中间自适应 */}
        <PixelPanel variant="blue" style={{ flex: 1, minWidth: 400, padding: 4, animationDelay: '0.15s' }}>
          <MapView onNPCClick={handleNPCClick} />
        </PixelPanel>

        {/* 右侧侧边栏 */}
        <PixelPanel
          variant="orange"
          className="pixel-theme"
          style={{
            width: SIDEBAR_WIDTH,
            flexShrink: 0,
            padding: 8,
            overflowY: 'auto',
            animationDelay: '0.25s',
          }}
        >
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            style={{ height: '100%' }}
            tabBarStyle={{ marginBottom: 8 }}
          />
        </PixelPanel>
      </div>

      {/* 邮箱悬浮图标和模态框 */}
      <MailboxIcon />
      <MailboxModal />

      {/* 表单悬浮图标和模态框 */}
      <FormIcon />
      <FormModal />
    </AppLayout>
  );
}

export default App;
