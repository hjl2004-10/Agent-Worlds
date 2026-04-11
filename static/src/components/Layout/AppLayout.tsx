import { Layout, Space } from 'antd';
import {
  RobotOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  SunOutlined,
  MoonOutlined,
} from '@ant-design/icons';
import { useStatusStore } from '@/store/useStatusStore';
import { useThemeStore } from '@/store/useThemeStore';
import { useLocaleStore } from '@/store/useLocaleStore';
import { useT } from '@/i18n';
import { PixelBanner, PixelButton } from '@/components/ui';
import { HelpModal } from './HelpModal';

const { Content } = Layout;

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { tick, npcCount, date, dateIso, time, period, periodKey } = useStatusStore();
  const locale = useLocaleStore((s) => s.locale);
  const { theme, toggle } = useThemeStore();
  const { toggle: toggleLocale } = useLocaleStore();
  const t = useT();

  return (
    <Layout style={{ minHeight: '100vh', background: 'var(--bg-body)' }}>
      {/* 像素风 Header */}
      <div
        style={{
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          gap: 12,
          position: 'relative',
        }}
      >
        {/* 左侧标题 */}
        <PixelBanner variant="style1" style={{ height: 40, minWidth: 120 }}>
          <Space>
            <RobotOutlined style={{
              fontSize: 18,
              color: '#4ade80',
              filter: 'drop-shadow(0 0 4px rgba(74, 222, 128, 0.5))',
            }} />
            <span style={{
              fontSize: 15,
              letterSpacing: 2,
              fontFamily: "'Press Start 2P', monospace",
              textShadow: '0 0 8px rgba(74, 222, 128, 0.3)',
            }}>
              {t('app.title')}
            </span>
            <span style={{ fontSize: 10, opacity: 0.6 }}>v2.0</span>
          </Space>
        </PixelBanner>

        {/* 中间状态指标 + 工具按钮 */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* 帮助按钮 */}
          <HelpModal />

          {/* 主题切换按钮 */}
          <PixelButton
            variant="style1"
            size="sm"
            onClick={toggle}
            title={theme === 'dark' ? t('header.toggleLight') : t('header.toggleDark')}
            style={{ minWidth: 36 }}
          >
            {theme === 'dark' ? (
              <SunOutlined style={{ fontSize: 14 }} />
            ) : (
              <MoonOutlined style={{ fontSize: 14 }} />
            )}
          </PixelButton>

          {/* 语言切换按钮 */}
          <PixelButton
            variant="style1"
            size="sm"
            onClick={toggleLocale}
            style={{ minWidth: 36, fontSize: 12, fontWeight: 700 }}
          >
            {t('header.switchLang')}
          </PixelButton>

          <PixelBanner variant="style2" style={{ height: 36 }}>
            <Space size={4}>
              <ThunderboltOutlined style={{
                color: '#4ade80',
                fontSize: 13,
                filter: 'drop-shadow(0 0 3px rgba(74, 222, 128, 0.4))',
              }} />
              <span style={{
                fontFamily: 'monospace',
                fontSize: 12,
                textShadow: '0 0 6px rgba(74, 222, 128, 0.2)',
              }}>
                Tick: {tick}
              </span>
            </Space>
          </PixelBanner>

          <PixelBanner variant="style3" style={{ height: 36 }}>
            <Space size={4}>
              <ClockCircleOutlined style={{ fontSize: 13 }} />
              <span style={{ fontSize: 12 }}>{locale === 'zh' ? date : dateIso}</span>
              <span style={{
                fontFamily: 'monospace',
                fontSize: 12,
                textShadow: '0 0 6px rgba(251, 191, 36, 0.2)',
              }}>
                {time}
              </span>
              <span style={{ fontSize: 10, opacity: 0.7 }}>({periodKey ? t(`period.${periodKey}`) : period})</span>
            </Space>
          </PixelBanner>

          <PixelBanner variant="style4" style={{ height: 36 }}>
            <Space size={4}>
              <TeamOutlined style={{ fontSize: 13 }} />
              <span style={{ fontSize: 12 }}>NPCs:</span>
              <span style={{
                fontFamily: 'monospace',
                fontWeight: 800,
                fontSize: 13,
                textShadow: '0 0 6px rgba(251, 191, 36, 0.3)',
              }}>
                {npcCount}
              </span>
            </Space>
          </PixelBanner>
        </div>

        {/* Header 底部渐变分割线 */}
        <div style={{
          position: 'absolute',
          bottom: 0,
          left: '10%',
          right: '10%',
          height: 1,
          background: 'linear-gradient(to right, transparent, rgba(56, 189, 248, 0.3), rgba(74, 222, 128, 0.3), rgba(56, 189, 248, 0.3), transparent)',
        }} />
      </div>

      <Content style={{ padding: '8px 16px 16px' }}>{children}</Content>
    </Layout>
  );
}
