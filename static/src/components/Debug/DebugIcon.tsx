/**
 * DebugIcon - 对话调试悬浮图标
 *
 * 点击打开 DebugPanel, 按 NPC 查看每次对话的请求/返回/工具调用。
 * 仿 MailboxIcon/FormIcon 的 DraggableButton 模式, 位置避开邮箱(-80)/表单(-140)。
 */
import { useState } from 'react';
import { BugOutlined } from '@ant-design/icons';
import { DraggableButton } from '@/components/ui';
import { DebugPanel } from '@/components/Debug/DebugPanel';

export function DebugIcon() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <DraggableButton
        icon={<BugOutlined style={{ fontSize: 22, color: '#3a2a1a' }} />}
        tooltip="对话调试 (请求/返回/工具)"
        backgroundColor="#722ed1"
        onClick={() => setOpen(true)}
        initialPosition={{ x: window.innerWidth - 400, y: window.innerHeight - 80 }}
      />
      <DebugPanel open={open} onClose={() => setOpen(false)} />
    </>
  );
}
