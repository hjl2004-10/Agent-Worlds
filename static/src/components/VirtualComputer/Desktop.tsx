/**
 * Desktop - 虚拟电脑桌面
 *
 * 显示应用图标网格
 */
import { useState } from 'react';
import type { Mail } from '@/api';

interface Background {
  id: string;
  name: string;
  color: string;
}

interface DesktopProps {
  mails: Mail[];
  htmlApps: Mail[];
  onOpenMail: () => void;
  onOpenHtmlApp: (mail: Mail) => void;
  onDeleteHtmlApp?: (mailId: string) => void;
  background: Background;
}

export function Desktop({ mails, htmlApps, onOpenMail, onOpenHtmlApp, onDeleteHtmlApp, background }: DesktopProps) {
  const unreadCount = mails.filter((m) => !m.read).length;
  const [contextMenu, setContextMenu] = useState<{ mailId: string; x: number; y: number } | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleContextMenu = (e: React.MouseEvent, mailId: string) => {
    e.preventDefault();
    setContextMenu({ mailId, x: e.clientX, y: e.clientY });
    setShowConfirm(false);
  };

  const handleDeleteClick = () => {
    setShowConfirm(true);
  };

  const handleConfirmDelete = () => {
    if (contextMenu && onDeleteHtmlApp) {
      onDeleteHtmlApp(contextMenu.mailId);
    }
    setContextMenu(null);
    setShowConfirm(false);
  };

  const handleClose = () => {
    setContextMenu(null);
    setShowConfirm(false);
  };

  return (
    <div className="desktop" style={{ background: background.color }} onClick={handleClose}>
      <div className="desktop-grid">
        {/* 邮箱应用 */}
        <div className="desktop-icon" onClick={onOpenMail}>
          <div className="icon-wrapper" style={{ position: 'relative' }}>
            <div className="icon-image mail-icon">📧</div>
            {unreadCount > 0 && (
              <span className="unread-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
            )}
          </div>
          <span className="icon-label">邮箱</span>
        </div>

        {/* HTML 应用图标 */}
        {htmlApps.map((app) => (
          <div
            key={app.id}
            className="desktop-icon"
            onClick={() => onOpenHtmlApp(app)}
            onContextMenu={(e) => handleContextMenu(e, app.id)}
            style={{ position: 'relative' }}
          >
            <div className="icon-image html-icon">
              {app.metadata?.icon || '🎮'}
            </div>
            <span className="icon-label">{app.title}</span>
          </div>
        ))}
      </div>

      {/* 右键菜单 - 渲染到 body 层级，避免定位问题 */}
      {contextMenu && onDeleteHtmlApp && (
        <div
          className="desktop-context-menu"
          style={{
            position: 'fixed',
            left: contextMenu.x,
            top: contextMenu.y,
            zIndex: 1000,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {!showConfirm ? (
            <div className="context-menu-item danger" onClick={handleDeleteClick}>
              删除
            </div>
          ) : (
            <div className="context-confirm">
              <div className="confirm-text">确定删除？</div>
              <div className="confirm-btns">
                <button className="confirm-btn yes" onClick={handleConfirmDelete}>删除</button>
                <button className="confirm-btn no" onClick={handleClose}>取消</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
