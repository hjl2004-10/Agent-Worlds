/**
 * MailboxIcon - 虚拟电脑悬浮图标
 *
 * 点击打开虚拟电脑界面
 * 点击外部 = 最小化 (隐藏但保留 iframe 状态)
 * 点击 X = 真正关闭 (销毁组件)
 */
import { useState, useEffect, useCallback } from 'react';
import { DraggableButton } from '@/components/ui';
import { useMailboxStore } from '@/store/useMailboxStore';
import { usePolling } from '@/hooks/usePolling';
import { VirtualComputer } from '@/components/VirtualComputer';

interface MailboxIconProps {
  pollInterval?: number;
}

export function MailboxIcon({ pollInterval = 5000 }: MailboxIconProps) {
  const {
    mails,
    unreadCount: storeUnreadCount,
    fetchUnreadCount,
    fetchInbox,
    markAsRead,
    markAllAsRead,
    deleteMail,
    toggleStar,
  } = useMailboxStore();

  // mails 加载后用实际数据，否则用 store 的 unreadCount（由轮询更新）
  const unreadCount = mails.length > 0
    ? mails.filter((m) => !m.read).length
    : storeUnreadCount;

  // alive = 组件已创建 (始终挂载在 DOM 中)
  // visible = 当前是否显示
  const [alive, setAlive] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    fetchUnreadCount();
  }, [fetchUnreadCount]);

  usePolling(() => {
    if (!visible) {
      fetchUnreadCount();
    }
  }, pollInterval);

  const handleClick = () => {
    fetchInbox();
    setAlive(true);
    setVisible(true);
  };

  // 最小化 = 隐藏 (不卸载，iframe 保留)
  const handleMinimize = useCallback(() => {
    setVisible(false);
  }, []);

  // 真正关闭 = 卸载组件 (iframe 销毁)
  const handleClose = useCallback(() => {
    setVisible(false);
    setAlive(false);
  }, []);

  return (
    <>
      <DraggableButton
        icon={<span style={{ fontSize: 22, lineHeight: 1 }}>💻</span>}
        tooltip={unreadCount > 0 ? `${unreadCount} 个新消息` : '虚拟电脑'}
        badgeCount={unreadCount}
        backgroundColor="#1890ff"
        onClick={handleClick}
        initialPosition={{ x: window.innerWidth - 80, y: window.innerHeight - 80 }}
      />

      {alive && (
        <VirtualComputer
          mails={mails}
          visible={visible}
          onMinimize={handleMinimize}
          onClose={handleClose}
          onMarkAsRead={markAsRead}
          onMarkAllAsRead={markAllAsRead}
          onDeleteMail={deleteMail}
          onToggleStar={toggleStar}
        />
      )}
    </>
  );
}
