/**
 * MailboxModal - 邮箱模态框
 *
 * 显示邮件列表和邮件详情
 * 支持已读/未读/星标/删除操作
 */
import { Modal, List, Button, Tag, Empty, Spin, Typography, Space, Popconfirm } from 'antd';
import {
  StarOutlined,
  StarFilled,
  DeleteOutlined,
  CheckOutlined,
  MailOutlined,
  FileTextOutlined,
  PictureOutlined,
  FileOutlined,
} from '@ant-design/icons';
import { useMailboxStore } from '@/store/useMailboxStore';
import type { Mail } from '@/api';
import { MailContent } from './MailContent';
import { useT } from '@/i18n';

const { Text } = Typography;

export function MailboxModal() {
  const t = useT();
  const {
    mails,
    loading,
    error,
    modalOpen,
    selectedMail,
    closeModal,
    selectMail,
    markAsRead,
    markAllAsRead,
    deleteMail,
    toggleStar,
  } = useMailboxStore();

  // 格式化时间
  const formatTime = (timeStr: string) => {
    const date = new Date(timeStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return t('mail.justNow');
    if (minutes < 60) return `${minutes} ${t('mail.minutesAgo')}`;
    if (hours < 24) return `${hours} ${t('mail.hoursAgo')}`;
    if (days < 7) return `${days} ${t('mail.daysAgo')}`;
    return date.toLocaleDateString('zh-CN');
  };

  // 获取内容类型图标
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'html':
        return <FileTextOutlined />;
      case 'image':
        return <PictureOutlined />;
      case 'document':
        return <FileOutlined />;
      default:
        return <MailOutlined />;
    }
  };

  // 获取内容类型标签颜色
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'html':
        return 'purple';
      case 'image':
        return 'cyan';
      case 'document':
        return 'geekblue';
      default:
        return 'blue';
    }
  };

  // 处理点击邮件
  const handleMailClick = async (mail: Mail) => {
    selectMail(mail);
    if (!mail.read) {
      await markAsRead(mail.id);
    }
  };

  // 处理全部已读
  const handleMarkAllRead = async () => {
    await markAllAsRead();
  };

  // 处理删除
  const handleDelete = async (mailId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteMail(mailId);
  };

  // 处理星标
  const handleToggleStar = async (mailId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await toggleStar(mailId);
  };

  // 渲染邮件列表
  const renderMailList = () => {
    if (loading) {
      return (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      );
    }

    if (error) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={`${t('mail.loadFailed')}: ${error}`}
          style={{ padding: 40 }}
        />
      );
    }

    if (mails.length === 0) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('mail.noMails')}
          style={{ padding: 40 }}
        />
      );
    }

    return (
      <List
        dataSource={mails}
        renderItem={(mail) => (
          <List.Item
            onClick={() => handleMailClick(mail)}
            style={{
              cursor: 'pointer',
              backgroundColor: mail.read ? 'transparent' : 'rgba(24, 144, 255, 0.25)',
              borderLeft: mail.read ? 'none' : '3px solid #1890ff',
              padding: '12px 16px',
              borderRadius: 4,
              marginBottom: 4,
            }}
          >
            <List.Item.Meta
              avatar={
                <span style={{ fontSize: 18, color: mail.read ? '#999' : '#1890ff' }}>
                  {getTypeIcon(mail.content_type)}
                </span>
              }
              title={
                <Space>
                  {!mail.read && <Tag color="red">{t('common.new')}</Tag>}
                  <Text strong={!mail.read} style={{ fontSize: 14, color: mail.read ? '#999' : '#fff' }}>
                    {mail.title}
                  </Text>
                  <Tag color={getTypeColor(mail.content_type)}>
                    {mail.content_type}
                  </Tag>
                </Space>
              }
              description={
                <Space split={<Text type="secondary">|</Text>}>
                  <Text type="secondary">{t('mail.from')} {mail.from}</Text>
                  <Text type="secondary">{formatTime(mail.created_at)}</Text>
                </Space>
              }
            />
            <Space>
              <Button
                type="text"
                size="small"
                icon={mail.starred ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
                onClick={(e) => handleToggleStar(mail.id, e)}
              />
              <Popconfirm
                title={t('mail.deleteConfirm')}
                onConfirm={(e) => handleDelete(mail.id, e as unknown as React.MouseEvent)}
                onCancel={(e) => e?.stopPropagation()}
                okText={t('common.delete')}
                cancelText={t('common.cancel')}
              >
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>
            </Space>
          </List.Item>
        )}
      />
    );
  };

  return (
    <>
      {/* 邮件列表模态框 */}
      <Modal
        title={
          <Space>
            <MailOutlined />
            <span>{t('mail.title')}</span>
            {mails.some((m) => !m.read) && (
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                onClick={handleMarkAllRead}
              >
                {t('mail.markAllRead')}
              </Button>
            )}
          </Space>
        }
        open={modalOpen && !selectedMail}
        onCancel={closeModal}
        footer={null}
        width={600}
        centered
      >
        <div style={{ maxHeight: 400, overflow: 'auto' }}>{renderMailList()}</div>
      </Modal>

      {/* 邮件详情模态框 */}
      <Modal
        title={
          selectedMail && (
            <Space>
              {getTypeIcon(selectedMail.content_type)}
              <span>{selectedMail.title}</span>
              <Tag color={getTypeColor(selectedMail.content_type)}>
                {selectedMail.content_type}
              </Tag>
            </Space>
          )
        }
        open={modalOpen && !!selectedMail}
        onCancel={() => selectMail(null)}
        footer={
          selectedMail && (
            <Space>
              <Button
                icon={selectedMail.starred ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
                onClick={() => toggleStar(selectedMail.id)}
              >
                {selectedMail.starred ? t('mail.unstar') : t('mail.star')}
              </Button>
              <Popconfirm
                title={t('mail.deleteConfirm')}
                onConfirm={() => deleteMail(selectedMail.id)}
                okText={t('common.delete')}
                cancelText={t('common.cancel')}
              >
                <Button danger icon={<DeleteOutlined />}>
                  {t('common.delete')}
                </Button>
              </Popconfirm>
              <Button type="primary" onClick={() => selectMail(null)}>
                {t('mail.backToList')}
              </Button>
            </Space>
          )
        }
        width={800}
        centered
      >
        {selectedMail && (
          <div>
            {/* 邮件头部信息 */}
            <div style={{ marginBottom: 16, paddingBottom: 16, borderBottom: '1px solid #f0f0f0' }}>
              <Space direction="vertical" size={4}>
                <Text>
                  <Text type="secondary">{t('mail.sender')}</Text>
                  {selectedMail.from}
                </Text>
                <Text>
                  <Text type="secondary">{t('mail.time')}</Text>
                  {new Date(selectedMail.created_at).toLocaleString('zh-CN')}
                </Text>
              </Space>
            </div>

            {/* 邮件内容 */}
            <MailContent mail={selectedMail} />
          </div>
        )}
      </Modal>
    </>
  );
}
