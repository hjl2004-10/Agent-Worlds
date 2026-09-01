import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import { DocsPage, isDocsHash } from './components/Docs/DocsPage';
import './index.css';
import './styles/pixel-ui.css';

/** 根级路由: #/docs 开头渲染文档站, 否则渲染主应用 */
function Root() {
  const [docsMode, setDocsMode] = useState(isDocsHash());
  useEffect(() => {
    const onHash = () => setDocsMode(isDocsHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  return docsMode ? <DocsPage /> : <App />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#4ade80',
          colorBgBase: '#0f0f1a',
          colorBgContainer: '#1a1a2e',
          colorBorder: '#2a2a4a',
          borderRadius: 6,
        },
      }}
    >
      <Root />
    </ConfigProvider>
  </React.StrictMode>
);
