/**
 * DraggableButton - 可拖拽的悬浮按钮
 */
import { Badge, Tooltip } from 'antd';
import React, { useState, useRef, useEffect, useCallback } from 'react';

interface Position {
  x: number;
  y: number;
}

interface DraggableButtonProps {
  icon: React.ReactNode;
  tooltip: string;
  badgeCount?: number;
  backgroundColor: string;
  disabled?: boolean;
  onClick?: () => void;
  initialPosition?: Position;
  onPositionChange?: (position: Position) => void;
}

export function DraggableButton({
  icon,
  tooltip,
  badgeCount = 0,
  backgroundColor,
  disabled = false,
  onClick,
  initialPosition,
  onPositionChange,
}: DraggableButtonProps) {
  const [position, setPosition] = useState<Position>(
    initialPosition || { x: window.innerWidth - 80, y: window.innerHeight - 80 }
  );
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, startPos: { x: 0, y: 0 } });

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // disabled 只影响点击，不影响拖动

    e.preventDefault();
    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startPos: { ...position },
    };
  }, [position]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;

    const deltaX = e.clientX - dragRef.current.startX;
    const deltaY = e.clientY - dragRef.current.startY;

    let newX = dragRef.current.startPos.x + deltaX;
    let newY = dragRef.current.startPos.y + deltaY;

    // 限制在屏幕范围内
    newX = Math.max(0, Math.min(newX, window.innerWidth - 56));
    newY = Math.max(0, Math.min(newY, window.innerHeight - 56));

    setPosition({ x: newX, y: newY });
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
      onPositionChange?.(position);
    }
  }, [isDragging, position, onPositionChange]);

  const handleClick = useCallback(() => {
    if (!isDragging && onClick) {
      onClick();
    }
  }, [isDragging, onClick]);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        zIndex: 1000,
        cursor: isDragging ? 'grabbing' : (disabled ? 'default' : 'grab'),
        userSelect: 'none',
      }}
      onMouseDown={handleMouseDown}
      onClick={handleClick}
    >
      <Tooltip title={tooltip}>
        <Badge count={badgeCount} size="small" offset={[-4, 4]}>
          <div
            style={{
              width: 48,
              height: 48,
              imageRendering: 'pixelated' as const,
              borderStyle: 'solid',
              borderWidth: 6,
              borderImage: `url('/ui/flat/${disabled ? 'UI_Flat_Button01a_4' : 'UI_Flat_Button02a_1'}.png') 6 fill stretch`,
              boxSizing: 'border-box' as const,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: isDragging ? 'grabbing' : (disabled ? 'default' : 'pointer'),
              transition: isDragging ? 'none' : 'transform 0.05s',
              opacity: disabled && badgeCount === 0 ? 0.5 : 1,
            }}
            onMouseEnter={(e) => {
              if (!disabled && !isDragging) {
                e.currentTarget.style.borderImage = "url('/ui/flat/UI_Flat_Button02a_2.png') 6 fill stretch";
                e.currentTarget.style.transform = 'scale(1.08)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isDragging) {
                e.currentTarget.style.borderImage = `url('/ui/flat/${disabled ? 'UI_Flat_Button01a_4' : 'UI_Flat_Button02a_1'}.png') 6 fill stretch`;
                e.currentTarget.style.transform = 'scale(1)';
              }
            }}
          >
            {icon}
          </div>
        </Badge>
      </Tooltip>
    </div>
  );
}
