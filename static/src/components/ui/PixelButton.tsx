/**
 * PixelButton - 像素风按钮（4态：正常/悬停/按下/禁用）
 */
import React from 'react';

interface PixelButtonProps {
  variant?: 'style1' | 'style2';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  onClick?: (e: React.MouseEvent) => void;
  children: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
  title?: string;
}

export function PixelButton({
  variant = 'style1',
  size = 'md',
  disabled = false,
  onClick,
  children,
  style,
  className = '',
  title,
}: PixelButtonProps) {
  return (
    <button
      className={`pixel-btn pixel-btn--${variant} pixel-btn--${size} ${disabled ? 'pixel-btn--disabled' : ''} ${className}`}
      disabled={disabled}
      onClick={onClick}
      style={style}
      title={title}
    >
      {children}
    </button>
  );
}
