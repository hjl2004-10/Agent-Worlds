/**
 * useDraggable - 可拖拽 Hook
 *
 * 让元素可以在屏幕上自由拖动
 */
import { useState, useRef, useCallback, useEffect } from 'react';

interface Position {
  x: number;
  y: number;
}

interface UseDraggableOptions {
  initialPosition?: Position;
  onDragEnd?: (position: Position) => void;
}

export function useDraggable(options: UseDraggableOptions = {}) {
  const { initialPosition, onDragEnd } = options;

  const [position, setPosition] = useState<Position>(
    initialPosition || { x: window.innerWidth - 72, y: window.innerHeight - 72 }
  );
  const [isDragging, setIsDragging] = useState(false);
  const dragStartPos = useRef<Position>({ x: 0, y: 0 });
  const elementStartPos = useRef<Position>({ x: 0, y: 0 });

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // 只响应左键
    if (e.button !== 0) return;

    e.preventDefault();
    setIsDragging(true);
    dragStartPos.current = { x: e.clientX, y: e.clientY };
    elementStartPos.current = { ...position };
  }, [position]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;

    const deltaX = e.clientX - dragStartPos.current.x;
    const deltaY = e.clientY - dragStartPos.current.y;

    let newX = elementStartPos.current.x + deltaX;
    let newY = elementStartPos.current.y + deltaY;

    // 限制在屏幕范围内
    const margin = 10;
    newX = Math.max(margin, Math.min(window.innerWidth - 48 - margin, newX));
    newY = Math.max(margin, Math.min(window.innerHeight - 48 - margin, newY));

    setPosition({ x: newX, y: newY });
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
      onDragEnd?.(position);
    }
  }, [isDragging, onDragEnd, position]);

  // 添加全局鼠标事件监听
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

  return {
    position,
    isDragging,
    dragHandlers: {
      onMouseDown: handleMouseDown,
      style: {
        position: 'fixed' as const,
        left: position.x,
        top: position.y,
        cursor: isDragging ? 'grabbing' : 'grab',
        userSelect: 'none' as const,
      },
    },
  };
}
