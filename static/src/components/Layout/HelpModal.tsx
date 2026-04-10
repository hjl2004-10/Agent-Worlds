import { useState } from 'react';
import { Modal } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { PixelButton } from '@/components/ui';

const SECTIONS = [
  {
    title: '地图操作',
    icon: '🗺️',
    items: [
      { key: '鼠标拖拽', desc: '平移视角' },
      { key: '滚轮', desc: '缩放 (0.5x ~ 3x)' },
      { key: '点击 NPC', desc: '选中并进入上帝模式' },
      { key: '右下角小地图', desc: '查看全局 + 视口范围' },
    ],
  },
  {
    title: '上帝模式',
    icon: '👑',
    items: [
      { key: 'WASD / 方向键', desc: '控制 NPC 移动' },
      { key: 'ESC', desc: '退出控制' },
      { key: '左侧 NPC 列表', desc: '点击切换控制目标' },
      { key: '指挥 Tab → 下达任务', desc: '给 NPC 分配任务 (如前往某地)' },
    ],
  },
  {
    title: '面板说明',
    icon: '📋',
    items: [
      { key: '指挥', desc: 'NPC 记忆查看 + 任务下达' },
      { key: '对话', desc: '以玩家身份与 NPC 实时对话' },
      { key: '动态', desc: 'NPC 之间的自动对话日志' },
      { key: '世界', desc: '世界观 / 场景设定管理' },
    ],
  },
  {
    title: 'NPC 状态图标',
    icon: '💬',
    items: [
      { key: '📧 信封', desc: '正在对话中' },
      { key: '⏱️ 计时器', desc: '刚开始移动' },
      { key: '💭 气泡', desc: '刚停下来 (思考中)' },
      { key: '灰色半透明', desc: 'NPC 已禁用' },
    ],
  },
  {
    title: '悬浮功能',
    icon: '✉️',
    items: [
      { key: '📬 邮箱图标', desc: 'NPC 之间的邮件系统' },
      { key: '📝 表单图标', desc: '查看 NPC 提交的表单' },
    ],
  },
  {
    title: '快捷操作',
    icon: '⚡',
    items: [
      { key: '☀️/🌙 按钮', desc: '切换亮色 / 暗色主题' },
      { key: 'NPC 配置面板', desc: '在 NPC 列表中点击齿轮图标' },
      { key: '窗口失焦', desc: '自动停止 NPC 移动 (防粘键)' },
    ],
  },
];

export function HelpModal() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <PixelButton
        variant="style1"
        size="sm"
        onClick={() => setOpen(true)}
        title="帮助"
        style={{ minWidth: 36 }}
      >
        <QuestionCircleOutlined style={{ fontSize: 14 }} />
      </PixelButton>

      <Modal
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        width={520}
        centered
        styles={{
          content: {
            background: 'var(--bg-card)',
            border: '2px solid var(--border-base)',
            borderRadius: 4,
            padding: 0,
            overflow: 'hidden',
          },
          header: { display: 'none' },
          mask: { background: 'rgba(0,0,0,0.6)' },
        }}
      >
        {/* 标题栏 */}
        <div style={{
          padding: '14px 20px 12px',
          borderBottom: '2px solid var(--border-base)',
          background: 'var(--bg-hover-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span style={{
            fontFamily: "'Press Start 2P', monospace",
            fontSize: 12,
            color: 'var(--primary-color)',
            letterSpacing: 1,
          }}>
            HELP
          </span>
        </div>

        {/* 内容区 */}
        <div style={{
          padding: '12px 16px 16px',
          maxHeight: '60vh',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}>
          {SECTIONS.map(section => (
            <div key={section.title}>
              {/* 区块标题 */}
              <div style={{
                fontFamily: "'Press Start 2P', monospace",
                fontSize: 9,
                color: 'var(--text-secondary)',
                marginBottom: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}>
                <span>{section.icon}</span>
                <span>{section.title}</span>
                <div style={{
                  flex: 1,
                  height: 1,
                  background: 'var(--border-base)',
                  marginLeft: 6,
                }} />
              </div>

              {/* 条目 */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {section.items.map(item => (
                  <div key={item.key} style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: 8,
                    padding: '3px 0',
                  }}>
                    <code style={{
                      fontFamily: "'Press Start 2P', monospace",
                      fontSize: 8,
                      color: '#fbbf24',
                      background: 'rgba(251, 191, 36, 0.08)',
                      padding: '2px 6px',
                      borderRadius: 2,
                      border: '1px solid rgba(251, 191, 36, 0.15)',
                      whiteSpace: 'nowrap',
                      flexShrink: 0,
                    }}>
                      {item.key}
                    </code>
                    <span style={{
                      fontSize: 12,
                      color: 'var(--text-primary)',
                      lineHeight: 1.4,
                    }}>
                      {item.desc}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* 底部提示 */}
          <div style={{
            marginTop: 4,
            padding: '8px 10px',
            background: 'rgba(74, 222, 128, 0.06)',
            border: '1px solid rgba(74, 222, 128, 0.12)',
            borderRadius: 3,
            fontSize: 11,
            color: 'var(--text-muted)',
            lineHeight: 1.6,
          }}>
            NPC 会自动在地图上漫步，相遇时触发 AI 对话。
            你可以用上帝模式控制 NPC 移动，或通过对话面板以玩家身份参与交互。
          </div>
        </div>
      </Modal>
    </>
  );
}
