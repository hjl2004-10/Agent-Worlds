/**
 * PixelPanel - 像素风九宫格拉伸面板
 */
import React from 'react';

interface PixelPanelProps {
  variant?: 'gray' | 'blue' | 'orange';
  children: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
}

export function PixelPanel({
  variant = 'gray',
  children,
  style,
  className = '',
}: PixelPanelProps) {
  return (
    <div
      className={`pixel-panel pixel-panel--${variant} ${className}`}
      style={style}
    >
      {children}
    </div>
  );
}
