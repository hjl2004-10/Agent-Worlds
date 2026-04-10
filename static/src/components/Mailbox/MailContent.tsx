/**
 * MailContent - 邮件内容渲染组件
 *
 * 根据邮件类型渲染不同内容:
 * - text: 纯文本 (支持 Markdown 渲染)
 * - html: HTML 沙盒
 * - image: 图片
 * - document: 文档链接
 */
import { Typography, Image, Alert, Space, Button } from 'antd';
import { FileOutlined, ExportOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import type { Mail } from '@/api';
import { mailboxApi } from '@/api';

const { Paragraph } = Typography;

interface MailContentProps {
  mail: Mail;
}

export function MailContent({ mail }: MailContentProps) {
  // 渲染纯文本 (支持 Markdown)
  const renderText = () => (
    <div
      style={{
        fontSize: 14,
        lineHeight: 1.8,
        color: 'var(--text-primary)',
      }}
    >
      <ReactMarkdown
        components={{
          // 自定义样式
          h1: ({ children }) => <h1 style={{ color: 'var(--text-white)', borderBottom: '1px solid #444', paddingBottom: 8 }}>{children}</h1>,
          h2: ({ children }) => <h2 style={{ color: 'var(--text-white)', borderBottom: '1px solid #444', paddingBottom: 6 }}>{children}</h2>,
          h3: ({ children }) => <h3 style={{ color: 'var(--text-white)' }}>{children}</h3>,
          p: ({ children }) => <p style={{ margin: '8px 0' }}>{children}</p>,
          code: ({ className, children }) => {
            const isInline = !className;
            return isInline ? (
              <code style={{ backgroundColor: '#333', padding: '2px 6px', borderRadius: 3, color: '#f81' }}>
                {children}
              </code>
            ) : (
              <pre style={{ backgroundColor: '#1a1a1a', padding: 12, borderRadius: 4, overflow: 'auto' }}>
                <code>{children}</code>
              </pre>
            );
          },
          blockquote: ({ children }) => (
            <blockquote style={{ borderLeft: '3px solid #1890ff', paddingLeft: 12, margin: '8px 0', color: 'var(--text-placeholder)' }}>
              {children}
            </blockquote>
          ),
          ul: ({ children }) => <ul style={{ paddingLeft: 20 }}>{children}</ul>,
          ol: ({ children }) => <ol style={{ paddingLeft: 20 }}>{children}</ol>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#1890ff' }}>
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%' }}>{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th style={{ border: '1px solid #444', padding: '8px 12px', backgroundColor: '#2a2a2a', textAlign: 'left' }}>
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td style={{ border: '1px solid #444', padding: '8px 12px' }}>
              {children}
            </td>
          ),
        }}
      >
        {mail.content}
      </ReactMarkdown>
    </div>
  );

  // 渲染 HTML (沙盒)
  const renderHtml = () => (
    <div
      style={{
        border: '1px solid #303030',
        borderRadius: 4,
        padding: 16,
        backgroundColor: '#1a1a1a',
        maxHeight: 500,
        overflow: 'auto',
      }}
    >
      {/* 使用 iframe 沙盒渲染 HTML */}
      <iframe
        srcDoc={mail.content}
        sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups allow-downloads"
        style={{
          width: '100%',
          minHeight: 350,
          border: 'none',
          backgroundColor: '#fff',
          borderRadius: 4,
        }}
        title="mail-html-content"
      />
    </div>
  );

  // 渲染图片
  const renderImage = () => {
    const imageUrl = mail.metadata?.image_url || mailboxApi.getFileUrl(mail.content);

    return (
      <div style={{ textAlign: 'center' }}>
        <Image
          src={imageUrl}
          alt={mail.title}
          style={{ maxWidth: '100%', maxHeight: 400 }}
          placeholder={
            <div style={{ width: '100%', height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              加载中...
            </div>
          }
          fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        />
        {mail.metadata?.description && (
          <Paragraph type="secondary" style={{ marginTop: 8 }}>
            {mail.metadata.description}
          </Paragraph>
        )}
      </div>
    );
  };

  // 渲染文档
  const renderDocument = () => {
    const format = mail.metadata?.doc_format || 'TXT';
    const filePath = mail.content;

    // 根据文档格式显示不同预览
    const formatIcons: Record<string, string> = {
      PDF: '📄 PDF',
      Word: '📝 Word',
      PPT: '📊 PPT',
      Excel: '📊 Excel',
      TXT: '📃 TXT',
      Markdown: '📋 Markdown',
      CSV: '📊 CSV',
      JSON: '📋 JSON',
      XML: '📋 XML',
      RTF: '📄 RTF',
    };

    // 是否为可预览的文本格式
    const isTextFormat = ['TXT', 'Markdown', 'CSV', 'JSON', 'XML'].includes(format);

    return (
      <div
        style={{
          padding: 24,
          backgroundColor: '#2a2a2a',
          borderRadius: 8,
          textAlign: 'center',
          color: 'var(--text-primary)',
        }}
      >
        <div style={{ fontSize: 48, marginBottom: 16 }}>
          {formatIcons[format] || '📎'}
        </div>
        <Paragraph strong style={{ fontSize: 16, marginBottom: 8, color: 'var(--text-white)' }}>
          {mail.title}
        </Paragraph>
        <Paragraph style={{ marginBottom: 16, color: 'var(--text-placeholder)' }}>
          格式: {format} | 路径: {filePath}
        </Paragraph>

        {/* 文档内容预览 */}
        {isTextFormat ? (
          <Alert
            type="info"
            message="文本文件"
            description="点击下方按钮打开或下载查看内容"
            style={{ marginBottom: 16, textAlign: 'left' }}
          />
        ) : (
          <Alert
            type="warning"
            message="文档预览"
            description="此文档格式需要下载查看"
            style={{ marginBottom: 16, textAlign: 'left' }}
          />
        )}

        <Space>
          <Button
            type="primary"
            icon={<ExportOutlined />}
            href={mailboxApi.getFileUrl(filePath)}
            target="_blank"
          >
            打开文件
          </Button>
          <Button icon={<FileOutlined />} href={mailboxApi.getFileUrl(filePath)} download>
            下载
          </Button>
        </Space>
      </div>
    );
  };

  // 根据类型渲染
  switch (mail.content_type) {
    case 'html':
      return renderHtml();
    case 'image':
      return renderImage();
    case 'document':
      return renderDocument();
    case 'text':
    default:
      return renderText();
  }
}
