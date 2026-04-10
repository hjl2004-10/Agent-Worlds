import { useEffect, useRef } from 'react';

type Direction = 'up' | 'down' | 'left' | 'right';

interface UseKeyboardOptions {
  onMove: (direction: Direction) => void;
  onStop: () => void;
  onEscape?: () => void;
  enabled?: boolean;
}

export function useKeyboard({
  onMove,
  onStop,
  onEscape,
  enabled = true,
}: UseKeyboardOptions) {
  // 追踪所有按下的方向键 (栈结构，最后按的优先)
  const pressedKeys = useRef<Set<Direction>>(new Set());
  const currentDirection = useRef<Direction | null>(null);
  const lastApiCall = useRef(0);
  const throttleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled) {
      // 禁用时清空状态
      pressedKeys.current.clear();
      currentDirection.current = null;
      return;
    }

    const keyMap: Record<string, Direction> = {
      ArrowUp: 'up',
      ArrowDown: 'down',
      ArrowLeft: 'left',
      ArrowRight: 'right',
      w: 'up',
      W: 'up',
      s: 'down',
      S: 'down',
      a: 'left',
      A: 'left',
      d: 'right',
      D: 'right',
    };

    const THROTTLE_MS = 80; // 后端 API 调用最小间隔

    const throttledMove = (direction: Direction) => {
      const now = Date.now();
      const elapsed = now - lastApiCall.current;

      if (throttleTimer.current) {
        clearTimeout(throttleTimer.current);
        throttleTimer.current = null;
      }

      if (elapsed >= THROTTLE_MS) {
        lastApiCall.current = now;
        onMove(direction);
      } else {
        // 延迟发送，确保最后一次方向不丢
        throttleTimer.current = setTimeout(() => {
          lastApiCall.current = Date.now();
          onMove(direction);
          throttleTimer.current = null;
        }, THROTTLE_MS - elapsed);
      }
    };

    const updateDirection = () => {
      const keys = pressedKeys.current;
      if (keys.size === 0) {
        if (currentDirection.current !== null) {
          currentDirection.current = null;
          if (throttleTimer.current) {
            clearTimeout(throttleTimer.current);
            throttleTimer.current = null;
          }
          onStop();
        }
        return;
      }

      // 最后按下的键优先 (取 Set 的最后一个元素)
      const lastKey = Array.from(keys).pop()!;
      if (lastKey !== currentDirection.current) {
        currentDirection.current = lastKey;
        throttledMove(lastKey);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      const direction = keyMap[e.key];
      if (direction) {
        e.preventDefault();
        // Set 中已有则先删后加，确保它排到最后（最新按的优先）
        pressedKeys.current.delete(direction);
        pressedKeys.current.add(direction);
        updateDirection();
      }
      if (e.key === 'Escape' && onEscape) {
        onEscape();
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const direction = keyMap[e.key];
      if (direction) {
        pressedKeys.current.delete(direction);
        updateDirection();
      }
    };

    // 失焦时停止移动 (防止"粘键")
    const handleBlur = () => {
      pressedKeys.current.clear();
      updateDirection();
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    window.addEventListener('blur', handleBlur);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('blur', handleBlur);
      if (throttleTimer.current) {
        clearTimeout(throttleTimer.current);
      }
    };
  }, [enabled, onMove, onStop, onEscape]);
}
