import { useState } from 'react';
import { Modal } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { PixelButton } from '@/components/ui';
import { useT } from '@/i18n';

export function HelpModal() {
  const t = useT();
  const [open, setOpen] = useState(false);

  const SECTIONS = [
    {
      title: t('help.section.map'),
      icon: '',
      items: [
        { key: t('help.map.drag'), desc: t('help.map.dragDesc') },
        { key: t('help.map.scroll'), desc: t('help.map.scrollDesc') },
        { key: t('help.map.clickNPC'), desc: t('help.map.clickNPCDesc') },
        { key: t('help.map.minimap'), desc: t('help.map.minimapDesc') },
      ],
    },
    {
      title: t('help.section.god'),
      icon: '',
      items: [
        { key: t('help.god.wasd'), desc: t('help.god.wasdDesc') },
        { key: t('help.god.esc'), desc: t('help.god.escDesc') },
        { key: t('help.god.npcList'), desc: t('help.god.npcListDesc') },
        { key: t('help.god.taskTab'), desc: t('help.god.taskTabDesc') },
      ],
    },
    {
      title: t('help.section.panels'),
      icon: '',
      items: [
        { key: t('help.panel.command'), desc: t('help.panel.commandDesc') },
        { key: t('help.panel.chat'), desc: t('help.panel.chatDesc') },
        { key: t('help.panel.activity'), desc: t('help.panel.activityDesc') },
        { key: t('help.panel.world'), desc: t('help.panel.worldDesc') },
      ],
    },
    {
      title: t('help.section.status'),
      icon: '',
      items: [
        { key: t('help.status.envelope'), desc: t('help.status.envelopeDesc') },
        { key: t('help.status.timer'), desc: t('help.status.timerDesc') },
        { key: t('help.status.bubble'), desc: t('help.status.bubbleDesc') },
        { key: t('help.status.dimmed'), desc: t('help.status.dimmedDesc') },
      ],
    },
    {
      title: t('help.section.floating'),
      icon: '',
      items: [
        { key: t('help.float.mailbox'), desc: t('help.float.mailboxDesc') },
        { key: t('help.float.form'), desc: t('help.float.formDesc') },
      ],
    },
    {
      title: t('help.section.shortcuts'),
      icon: '',
      items: [
        { key: t('help.shortcut.theme'), desc: t('help.shortcut.themeDesc') },
        { key: t('help.shortcut.npcConfig'), desc: t('help.shortcut.npcConfigDesc') },
        { key: t('help.shortcut.blur'), desc: t('help.shortcut.blurDesc') },
      ],
    },
  ];

  return (
    <>
      <PixelButton
        variant="style1"
        size="sm"
        onClick={() => setOpen(true)}
        title={t('help.title')}
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
            {t('help.footer')}
          </div>
        </div>
      </Modal>
    </>
  );
}
