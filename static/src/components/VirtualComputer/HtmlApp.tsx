/**
 * HtmlApp - HTML 应用渲染器
 *
 * 核心功能:
 * - iframe 100% 铺满容器，内容自适应
 * - 手动缩放 + 拖拽平移
 * - 手动刷新
 * - 支持 JS 执行
 */
import { useRef, useEffect, useState, useCallback } from 'react';
import { Button, Tooltip, Popconfirm } from 'antd';
import { ArrowLeftOutlined, DragOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import type { Mail } from '@/api';
import type { DeviceMode } from './VirtualComputer';

interface HtmlAppProps {
  mail: Mail;
  deviceMode: DeviceMode;
  scale: number;
  onBack: () => void;
  onScaleChange: (scale: number) => void;
  onDelete?: (mailId: string) => void;
}

export function HtmlApp({ mail, deviceMode, scale, onBack, onScaleChange, onDelete }: HtmlAppProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const isMobile = deviceMode === 'mobile';

  // 拖拽状态
  const [isDragging, setIsDragging] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragStart = useRef({ x: 0, y: 0, offsetX: 0, offsetY: 0 });

  // 拖拽模式开关
  const [dragMode, setDragMode] = useState(false);

  // 刷新 key (改变时触发重新加载)
  const [refreshKey, setRefreshKey] = useState(0);

  // 当前 blob URL 引用
  const currentBlobUrlRef = useRef<string>('');

  // 设备模式变化时重置
  useEffect(() => {
    setOffset({ x: 0, y: 0 });
    onScaleChange(1);
  }, [deviceMode, mail.id, onScaleChange]);

  // 手动刷新
  const handleRefresh = () => {
    setRefreshKey((k) => k + 1);
    setOffset({ x: 0, y: 0 });
  };

  // 拖拽开始
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0 || !dragMode) return;
    setIsDragging(true);
    dragStart.current = {
      x: e.clientX,
      y: e.clientY,
      offsetX: offset.x,
      offsetY: offset.y,
    };
    e.preventDefault();
  };

  // 拖拽移动
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;

      const deltaX = (e.clientX - dragStart.current.x) / scale;
      const deltaY = (e.clientY - dragStart.current.y) / scale;

      setOffset({
        x: dragStart.current.offsetX + deltaX,
        y: dragStart.current.offsetY + deltaY,
      });
    },
    [isDragging, scale]
  );

  // 拖拽结束
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // 绑定全局鼠标事件
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // 提取 HTML 内容
  const extractHtml = useCallback((content: string) => {
    const htmlMatch = content.match(/```(?:html|)\s*\n?([\s\S]*?)\n?\s*```/);
    if (htmlMatch) {
      return htmlMatch[1].trim();
    }
    return content;
  }, []);

  // 包装 HTML 内容 - 自适应铺满容器
  const wrapHtml = useCallback((htmlContent: string) => {
    const cleanHtml = extractHtml(htmlContent);
    const trimmed = cleanHtml.trim();

    // 如果已经是完整 HTML 文档，直接使用
    if (/^<!DOCTYPE\s/i.test(trimmed) || /^<html[\s>]/i.test(trimmed)) {
      return cleanHtml;
    }

    // 片段内容才包装 - 100% 自适应
    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      width: 100%;
      height: 100%;
      overflow: auto;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    ${isMobile ? `
    /* 手机模式优化 */
    -webkit-text-size-adjust: 100%;
    -webkit-tap-highlight-color: transparent;
    * { -webkit-overflow-scrolling: touch; }
    ` : ''}
  </style>
</head>
<body>
${cleanHtml}
</body>
</html>
    `;
  }, [isMobile, extractHtml]);

  // 加载 HTML 到 iframe
  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    // 清理旧的 blob URL
    if (currentBlobUrlRef.current) {
      URL.revokeObjectURL(currentBlobUrlRef.current);
      currentBlobUrlRef.current = '';
    }

    const wrappedHtml = wrapHtml(mail.content);
    const blob = new Blob([wrappedHtml], { type: 'text/html; charset=utf-8' });
    const blobUrl = URL.createObjectURL(blob);
    currentBlobUrlRef.current = blobUrl;

    iframe.src = blobUrl;

    const handleLoad = () => {
      if (currentBlobUrlRef.current === blobUrl) {
        URL.revokeObjectURL(blobUrl);
        currentBlobUrlRef.current = '';
      }
    };
    iframe.addEventListener('load', handleLoad, { once: true });

    return () => {
      iframe.removeEventListener('load', handleLoad);
    };
  }, [mail.content, wrapHtml, refreshKey]); // refreshKey 变化时重新加载

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (currentBlobUrlRef.current) {
        URL.revokeObjectURL(currentBlobUrlRef.current);
      }
    };
  }, []);

  return (
    <div className="html-app">
      {/* 顶部返回栏 */}
      <div className="html-app-header">
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={onBack}
          style={{ color: 'var(--text-white)', padding: 0 }}
        >
          返回
        </Button>
        <span className="html-app-title">{mail.title}</span>
        <span className="html-app-info">
          {isMobile ? '手机模式' : '电脑模式'} · {Math.round(scale * 100)}%
        </span>
        {/* 刷新按钮 */}
        <Tooltip title="刷新">
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            style={{ color: 'var(--text-icon-muted)', marginLeft: 8 }}
            size="small"
          />
        </Tooltip>
        {/* 拖拽模式开关 */}
        <Tooltip title={dragMode ? '拖拽模式：开启' : '拖拽模式：关闭'}>
          <Button
            type={dragMode ? 'primary' : 'text'}
            icon={<DragOutlined />}
            onClick={() => setDragMode(!dragMode)}
            style={{ color: dragMode ? '#fff' : '#888', marginLeft: 4 }}
            size="small"
          />
        </Tooltip>
        {/* 删除按钮 */}
        {onDelete && (
          <Popconfirm
            title="确定删除此应用？"
            onConfirm={() => { onDelete(mail.id); onBack(); }}
            okText="删除"
            cancelText="取消"
          >
            <Button
              type="text"
              icon={<DeleteOutlined />}
              style={{ color: '#ff4d4f', marginLeft: 4 }}
              size="small"
            />
          </Popconfirm>
        )}
      </div>

      {/* 视口容器 */}
      <div
        ref={containerRef}
        className="html-viewport"
        {...(dragMode ? { onMouseDown: handleMouseDown } : {})}
        style={{ cursor: dragMode ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
      >
        {/* iframe - 100% 铺满容器，内容自适应 */}
        <iframe
          ref={iframeRef}
          className="html-iframe"
          sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups allow-downloads"
          style={{
            transform: `scale(${scale}) translate(${offset.x}px, ${offset.y}px)`,
            transformOrigin: 'top center',
          }}
          title={mail.title}
        />
      </div>
    </div>
  );
}
