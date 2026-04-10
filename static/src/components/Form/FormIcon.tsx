/**
 * FormIcon - 表单悬浮图标
 */
import { FormOutlined } from '@ant-design/icons';
import { DraggableButton } from '@/components/ui';
import { useFormStore } from '@/store/useFormStore';
import { usePolling } from '@/hooks/usePolling';
import { useEffect } from 'react';

interface FormIconProps {
  pollInterval?: number;
}

export function FormIcon({ pollInterval = 3000 }: FormIconProps) {
  const { pendingCount, fetchPendingForms, forms, openForm } = useFormStore();

  useEffect(() => {
    fetchPendingForms();
  }, [fetchPendingForms]);

  usePolling(() => {
    fetchPendingForms();
  }, pollInterval);

  const handleClick = () => {
    if (forms.length > 0) {
      openForm(forms[0]);
    }
  };

  return (
    <DraggableButton
      icon={<FormOutlined style={{ fontSize: 22, color: '#3a2a1a' }} />}
      tooltip={pendingCount > 0 ? `${pendingCount} 个待处理表单` : '表单'}
      badgeCount={pendingCount}
      backgroundColor="#52c41a"
      disabled={pendingCount === 0}
      onClick={handleClick}
      initialPosition={{ x: window.innerWidth - 140, y: window.innerHeight - 80 }}
    />
  );
}
