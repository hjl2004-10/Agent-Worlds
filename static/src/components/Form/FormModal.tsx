/**
 * FormModal - 表单模态框
 *
 * 显示人类问题并等待文字回复
 */
import { Modal, Button, Typography, Space, Input, Alert, Divider } from 'antd';
import { QuestionCircleOutlined, CheckOutlined, CloseOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useFormStore } from '@/store/useFormStore';
import type { FormResponse } from '@/api';
import { useState } from 'react';
import { useT } from '@/i18n';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

export function FormModal() {
  const t = useT();
  const {
    currentForm,
    closeForm,
    submitForm,
    cancelForm,
    error,
  } = useFormStore();

  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 格式化剩余时间
  const formatRemainingTime = (expiresAt: number) => {
    const remaining = Math.max(0, expiresAt - Date.now() / 1000);
    if (remaining < 60) return `${Math.floor(remaining)} ${t('form.seconds')}`;
    if (remaining < 3600) return `${Math.floor(remaining / 60)} ${t('form.minutes')}`;
    return `${Math.floor(remaining / 3600)} ${t('form.hours')}`;
  };

  // 处理提交
  const handleSubmit = async () => {
    if (!currentForm || !answer.trim()) return;

    setSubmitting(true);
    const success = await submitForm(currentForm.id, { answer: answer.trim() } as FormResponse);
    if (success) {
      setAnswer('');
    }
    setSubmitting(false);
  };

  // 处理取消
  const handleCancel = async () => {
    if (!currentForm) return;
    await cancelForm(currentForm.id);
    setAnswer('');
  };

  // 处理关闭
  const handleClose = () => {
    closeForm();
    setAnswer('');
  };

  if (!currentForm) return null;

  return (
    <Modal
      title={
        <Space>
          <QuestionCircleOutlined style={{ color: '#52c41a' }} />
          <span>{currentForm.from_npc} {t('form.question')}</span>
        </Space>
      }
      open={!!currentForm}
      onCancel={handleClose}
      width={600}
      centered
      footer={
        <Space>
          <Button icon={<CloseOutlined />} onClick={handleCancel} danger>
            {t('form.cancelBtn')}
          </Button>
          <Button onClick={handleClose}>
            {t('form.later')}
          </Button>
          <Button
            type="primary"
            icon={<CheckOutlined />}
            loading={submitting}
            disabled={!answer.trim()}
            onClick={handleSubmit}
          >
            {t('form.submit')}
          </Button>
        </Space>
      }
    >
      <div>
        {/* 问题信息 */}
        <div style={{ marginBottom: 16 }}>
          <Space direction="vertical" size={4}>
            <Text type="secondary">
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {t('form.remaining')} {formatRemainingTime(currentForm.expires_at)}
            </Text>
          </Space>
        </div>

        {/* 问题内容 */}
        <div
          style={{
            padding: 16,
            backgroundColor: '#2a2a2a',
            borderRadius: 8,
            marginBottom: 16,
          }}
        >
          <Paragraph
            style={{
              color: 'var(--text-white)',
              fontSize: 16,
              margin: 0,
              whiteSpace: 'pre-wrap',
            }}
          >
            {currentForm.title}
          </Paragraph>
        </div>

        {/* 背景说明 */}
        {currentForm.description && currentForm.description !== currentForm.title && (
          <Alert
            type="info"
            message={currentForm.description}
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 错误提示 */}
        {error && (
          <Alert
            type="error"
            message={error}
            style={{ marginBottom: 16 }}
          />
        )}

        <Divider />

        {/* 回复输入 */}
        <div style={{ marginTop: 16 }}>
          <Text style={{ color: 'var(--text-primary)', marginBottom: 8, display: 'block' }}>
            {t('form.yourReply')}
          </Text>
          <TextArea
            rows={4}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder={t('form.replyPlaceholder')}
            style={{
              backgroundColor: '#1a1a1a',
              color: 'var(--text-white)',
              border: '1px solid #444',
            }}
            autoFocus
          />
        </div>
      </div>
    </Modal>
  );
}
