/**
 * VirtualComputer - 虚拟电脑组件
 *
 * 模拟一个独立的电脑/手机界面，用于展示 HTML 应用和邮箱
 * 支持:
 * - 设备模式切换 (手机竖屏/电脑横屏)
 * - 拖拽平移
 * - 背景图切换
 * - 固定/钉子功能 (锁定界面)
 * - 状态持久化 (最小化重开不丢失)
 * - 最小化 vs 关闭区分
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { HomeOutlined } from '@ant-design/icons';
import { Desktop } from './Desktop';
import { MailApp } from './MailApp';
import { HtmlApp } from './HtmlApp';
import { SettingsPanel } from './SettingsPanel';
import type { Mail } from '@/api';
import './VirtualComputer.css';

// 视口预设
export const VIEWPORT_PRESETS = {
  mobile: { width: 393, height: 852, name: '手机竖屏' },
  desktop: { width: 800, height: 600, name: '电脑横屏' },
};

// 背景图预设
export const BACKGROUNDS = [
  { id: 'default', name: '默认', color: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' },
  { id: 'sunset', name: '日落', color: 'linear-gradient(135deg, #ff6b6b 0%, #feca57 100%)' },
  { id: 'ocean', name: '海洋', color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { id: 'forest', name: '森林', color: 'linear-gradient(135deg, #134e5e 0%, #71b280 100%)' },
  { id: 'night', name: '星空', color: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)' },
  { id: 'cyber', name: '赛博', color: 'linear-gradient(135deg, #0d0d0d 0%, #1a1a1a 50%, #0d0d0d 100%)' },
];

export type DeviceMode = 'mobile' | 'desktop';
export type AppType = 'desktop' | 'mail' | 'html';

interface VirtualComputerProps {
  mails: Mail[];
  visible: boolean;
  onMinimize: () => void;
  onClose: () => void;
  onMarkAsRead: (mailId: string) => void;
  onMarkAllAsRead: () => void;
  onDeleteMail: (mailId: string) => void;
  onToggleStar: (mailId: string) => void;
}

// 持久化状态接口
interface PersistedState {
  deviceMode: DeviceMode;
  backgroundId: string;
  scale: number;
  currentApp: AppType;
  selectedMailId: string | null;
}

// 从 localStorage 加载状态
const loadState = (): PersistedState | null => {
  try {
    const saved = localStorage.getItem('virtual-computer-state');
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (e) {
    console.error('Failed to load virtual computer state:', e);
  }
  return null;
};

// 保存状态到 localStorage
const saveState = (state: PersistedState) => {
  try {
    localStorage.setItem('virtual-computer-state', JSON.stringify(state));
  } catch (e) {
    console.error('Failed to save virtual computer state:', e);
  }
};

// 清除状态
const clearState = () => {
  try {
    localStorage.removeItem('virtual-computer-state');
  } catch (e) {
    console.error('Failed to clear virtual computer state:', e);
  }
};

export function VirtualComputer({
  mails,
  visible,
  onMinimize,
  onClose,
  onMarkAsRead,
  onMarkAllAsRead,
  onDeleteMail,
  onToggleStar,
}: VirtualComputerProps) {
  // 从持久化状态恢复
  const savedState = useRef(loadState());

  // 状态
  const [deviceMode, setDeviceMode] = useState<DeviceMode>(savedState.current?.deviceMode || 'desktop');
  const [currentApp, setCurrentApp] = useState<AppType>(savedState.current?.currentApp || 'desktop');
  const [backgroundId, setBackgroundId] = useState(savedState.current?.backgroundId || 'default');
  const [scale, setScale] = useState(savedState.current?.scale || 1);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [time, setTime] = useState(new Date());

  // 从保存的 mailId 恢复选中的邮件
  const [selectedMailId, setSelectedMailId] = useState<string | null>(savedState.current?.selectedMailId || null);
  const selectedMail = mails.find((m) => m.id === selectedMailId) || null;

  // 背景图
  const background = BACKGROUNDS.find((b) => b.id === backgroundId) || BACKGROUNDS[0];

  // 选中的邮件被删除时，自动返回桌面
  useEffect(() => {
    if (selectedMailId && !selectedMail && currentApp === 'html') {
      setCurrentApp('desktop');
      setSelectedMailId(null);
    }
  }, [selectedMailId, selectedMail, currentApp]);

  // 时钟更新
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // 持久化状态 (最小化时保留，下次恢复)
  useEffect(() => {
    const state: PersistedState = {
      deviceMode,
      backgroundId,
      scale,
      currentApp,
      selectedMailId,
    };
    saveState(state);
  }, [deviceMode, backgroundId, scale, currentApp, selectedMailId]);

  // 分离邮件: 普通邮件 vs HTML应用
  const normalMails = mails.filter((m) => m.content_type !== 'html_app' && m.content_type !== 'html');
  const htmlApps = mails.filter((m) => m.content_type === 'html_app' || m.content_type === 'html');

  // 打开应用
  const openApp = (app: AppType) => {
    setCurrentApp(app);
    if (app !== 'html') {
      setSelectedMailId(null);
    }
  };

  // 返回桌面
  const goHome = () => {
    setCurrentApp('desktop');
    setSelectedMailId(null);
  };

  // 打开 HTML 应用
  const openHtmlApp = (mail: Mail) => {
    setSelectedMailId(mail.id);
    setCurrentApp('html');
    // HTML 应用打开时自动标为已读（不显示未读提示）
    if (!mail.read) {
      onMarkAsRead(mail.id);
    }
    // 根据邮件的 device_mode 设置视口
    const mode = mail.metadata?.device_mode as DeviceMode;
    if (mode === 'desktop' || mode === 'mobile') {
      setDeviceMode(mode);
    }
  };

  // 点击外部 = 最小化（隐藏但不卸载，iframe 保留）
  const handleMinimize = useCallback(() => {
    onMinimize();
  }, [onMinimize]);

  // 点击 X = 真正关闭（卸载组件，iframe 销毁）
  const handleClose = useCallback(() => {
    clearState();
    onClose();
  }, [onClose]);

  // 渲染当前应用
  const renderCurrentApp = () => {
    switch (currentApp) {
      case 'mail':
        return (
          <MailApp
            mails={normalMails}
            onBack={goHome}
            onSelectMail={(mail) => {
              setSelectedMailId(mail.id);
              onMarkAsRead(mail.id);
            }}
            selectedMail={selectedMail}
            onMarkAllAsRead={onMarkAllAsRead}
            onDeleteMail={onDeleteMail}
            onToggleStar={onToggleStar}
          />
        );
      case 'html':
        return selectedMail ? (
          <HtmlApp
            mail={selectedMail}
            deviceMode={deviceMode}
            scale={scale}
            onBack={goHome}
            onScaleChange={setScale}
            onDelete={(mailId) => {
              onDeleteMail(mailId);
              goHome();
            }}
          />
        ) : (
          <div className="empty-state">请选择一个应用</div>
        );
      case 'desktop':
      default:
        return (
          <Desktop
            mails={normalMails}
            htmlApps={htmlApps}
            onOpenMail={() => openApp('mail')}
            onOpenHtmlApp={openHtmlApp}
            onDeleteHtmlApp={onDeleteMail}
            background={background}
          />
        );
    }
  };

  return (
    <div className="virtual-computer-overlay" onClick={handleMinimize} style={{ display: visible ? undefined : 'none' }}>
      <div
        className={`virtual-computer-frame ${deviceMode === 'mobile' ? 'mobile-mode' : 'desktop-mode'}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 屏幕区域 */}
        <div className="virtual-screen" style={{ background: background.color }}>
          {/* 应用内容 */}
          <div className="app-container">
            {renderCurrentApp()}
          </div>
        </div>

        {/* 状态栏 */}
        <div className="status-bar">
          {/* 左侧: 返回按钮 */}
          <div className="status-left">
            {currentApp !== 'desktop' && (
              <button className="status-btn" onClick={goHome} title="返回桌面">
                <HomeOutlined />
              </button>
            )}
          </div>

          {/* 中间: 控制按钮 */}
          <div className="status-center">
            <button
              className="status-btn minimize-btn"
              onClick={handleMinimize}
              title="最小化 (点击外部区域也可最小化)"
            >
              −
            </button>
            <button
              className="status-btn"
              onClick={() => setDeviceMode(deviceMode === 'mobile' ? 'desktop' : 'mobile')}
              title={deviceMode === 'mobile' ? '切换到电脑模式' : '切换到手机模式'}
            >
              {deviceMode === 'mobile' ? '🖥️' : '📱'}
            </button>
            <button
              className="status-btn"
              onClick={() => setSettingsOpen(!settingsOpen)}
              title="设置"
            >
              ⚙️
            </button>
            <button
              className="status-btn close-btn"
              onClick={handleClose}
              title="关闭 (清除状态)"
            >
              ✕
            </button>
          </div>

          {/* 右侧: 时间 */}
          <div className="status-right">
            <span className="time">{time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        </div>

        {/* 设置面板 */}
        {settingsOpen && (
          <SettingsPanel
            backgroundId={backgroundId}
            onBackgroundChange={setBackgroundId}
            scale={scale}
            onScaleChange={setScale}
            onClose={() => setSettingsOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
