/**
 * PixelBanner - 像素风横幅标题
 */
import React from 'react';

interface PixelBannerProps {
  variant?: 'style1' | 'style2' | 'style3' | 'style4';
  children: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
}

export function PixelBanner({
  variant = 'style1',
  children,
  style,
  className = '',
}: PixelBannerProps) {
  return (
    <div
      className={`pixel-banner pixel-banner--${variant} ${className}`}
      style={style}
    >
      {children}
    </div>
  );
}
