import { useState, useRef } from 'react';
import {
  Modal,
  Button,
  Checkbox,
  List,
  Typography,
  Space,
  Tag,
  message,
  Divider,
  Alert,
} from 'antd';
import {
  ExportOutlined,
  ImportOutlined,
  DownloadOutlined,
  UploadOutlined,
  FileOutlined,
} from '@ant-design/icons';
import type { NPC } from '@/api/types';
import type { NPCExportData } from '@/api/types';
import { exportNPCs, importNPCs } from '@/api/god';
import { useT } from '@/i18n';

const { Text } = Typography;

interface NPCImportExportProps {
  open: boolean;
  onClose: () => void;
  npcs: NPC[];
  onSuccess: () => void;
}

export function NPCImportExport({ open, onClose, npcs, onSuccess }: NPCImportExportProps) {
  const t = useT();
  const [mode, setMode] = useState<'select' | 'export' | 'import'>('select');
  const [selectedNPCs, setSelectedNPCs] = useState<string[]>([]);
  const [overwrite, setOverwrite] = useState(false);
  const [loading, setLoading] = useState(false);
  const [importData, setImportData] = useState<NPCExportData[] | null>(null);
  const [importPreview, setImportPreview] = useState<{ name: string; exists: boolean }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExport = async () => {
    if (selectedNPCs.length === 0) {
      message.warning(t('ie.warnSelectOne'));
      return;
    }

    setLoading(true);
    try {
      const { data } = await exportNPCs(selectedNPCs);
      if (data.status === 'ok' && data.npcs) {
        // 创建下载文件
        const exportData = {
          version: '1.0',
          type: 'NPC_GROUP',
          exported_at: new Date().toISOString(),
          npcs: data.npcs,
        };
        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
          type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `npc_export_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);

        message.success(`${t('ie.exportSuccess')} ${data.exported_count} ${t('ie.exportCount')}`);
        if (data.not_found && data.not_found.length > 0) {
          message.warning(`${t('ie.notFound')} ${data.not_found.join(', ')}`);
        }
        handleClose();
      } else {
        message.error(data.message || t('common.exportFailed'));
      }
    } catch (error) {
      message.error(t('common.exportFailed'));
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = JSON.parse(event.target?.result as string);
        let npcsData: NPCExportData[] = [];

        // 支持两种格式: 直接数组或包装对象
        if (Array.isArray(content)) {
          npcsData = content;
        } else if (content.npcs && Array.isArray(content.npcs)) {
          npcsData = content.npcs;
        } else {
          message.error(t('ie.invalidFormat'));
          return;
        }

        setImportData(npcsData);

        // 预览: 检查哪些 NPC 已存在
        const preview = npcsData.map((npc) => ({
          name: npc.header?.name || 'Unknown',
          exists: npcs.some((n) => n.name.toLowerCase() === npc.header?.name?.toLowerCase()),
        }));
        setImportPreview(preview);
        setMode('import');
      } catch (error) {
        message.error(t('ie.parseFailed'));
        console.error(error);
      }
    };
    reader.readAsText(file);

    // 重置 input，允许重复选择同一文件
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleImport = async () => {
    if (!importData || importData.length === 0) {
      message.warning(t('ie.noData'));
      return;
    }

    setLoading(true);
    try {
      const { data } = await importNPCs(importData, overwrite);
      if (data.status === 'ok') {
        message.success(`${t('ie.importSuccess')} ${data.imported_count} ${t('ie.exportCount')}`);
        if (data.skipped && data.skipped.length > 0) {
          message.info(`${t('ie.skipped')} ${data.skipped.join(', ')}`);
        }
        if (data.errors && data.errors.length > 0) {
          message.warning(`${t('ie.errors')} ${data.errors.join(', ')}`);
        }
        onSuccess();
        handleClose();
      } else {
        message.error(data.message || t('common.importFailed'));
      }
    } catch (error) {
      message.error(t('common.importFailed'));
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setMode('select');
    setSelectedNPCs([]);
    setOverwrite(false);
    setImportData(null);
    setImportPreview([]);
    onClose();
  };

  const toggleNPC = (name: string) => {
    setSelectedNPCs((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const selectAll = () => {
    setSelectedNPCs(npcs.map((n) => n.name));
  };

  const deselectAll = () => {
    setSelectedNPCs([]);
  };

  return (
    <Modal
      title={
        <Space>
          <FileOutlined />
          {t('ie.title')}
        </Space>
      }
      open={open}
      onCancel={handleClose}
      footer={null}
      width={600}
    >
      {mode === 'select' && (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Button
            type="primary"
            icon={<ExportOutlined />}
            size="large"
            block
            onClick={() => setMode('export')}
          >
            {t('ie.exportBtn')}
          </Button>
          <Button
            icon={<ImportOutlined />}
            size="large"
            block
            onClick={() => fileInputRef.current?.click()}
          >
            {t('ie.importBtn')}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
        </Space>
      )}

      {mode === 'export' && (
        <div>
          <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
            <Text>{t('ie.selectExport')}</Text>
            <Space>
              <Button size="small" onClick={selectAll}>
                {t('ie.selectAll')}
              </Button>
              <Button size="small" onClick={deselectAll}>
                {t('ie.deselectAll')}
              </Button>
            </Space>
          </div>
          <div
            style={{
              maxHeight: 300,
              overflowY: 'auto',
              border: '1px solid var(--border-primary)',
              borderRadius: 4,
              padding: 8,
            }}
          >
            <List
              dataSource={npcs}
              renderItem={(npc) => (
                <List.Item
                  style={{ padding: '4px 8px', cursor: 'pointer' }}
                  onClick={() => toggleNPC(npc.name)}
                >
                  <Checkbox checked={selectedNPCs.includes(npc.name)}>
                    <Space>
                      <Text>{npc.name}</Text>
                      {npc.is_player && <Tag color="cyan">{t('npc.status.player')}</Tag>}
                      <Text type="secondary">({npc.x.toFixed(0)}, {npc.y.toFixed(0)})</Text>
                    </Space>
                  </Checkbox>
                </List.Item>
              )}
            />
          </div>
          <Divider />
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setMode('select')}>{t('common.back')}</Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              loading={loading}
              onClick={handleExport}
            >
              {t('common.export')} ({selectedNPCs.length})
            </Button>
          </Space>
        </div>
      )}

      {mode === 'import' && (
        <div>
          <Alert
            message={`${t('ie.importConfirm')} ${importData?.length || 0} ${t('ie.exportCount')}`}
            description={t('ie.importHint')}
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
          />
          <div
            style={{
              maxHeight: 250,
              overflowY: 'auto',
              border: '1px solid var(--border-primary)',
              borderRadius: 4,
              padding: 8,
              marginBottom: 12,
            }}
          >
            <List
              dataSource={importPreview}
              renderItem={(item) => (
                <List.Item style={{ padding: '4px 8px' }}>
                  <Space>
                    <Text>{item.name}</Text>
                    {item.exists && <Tag color="orange">{t('ie.exists')}</Tag>}
                    {!item.exists && <Tag color="green">{t('common.new')}</Tag>}
                  </Space>
                </List.Item>
              )}
            />
          </div>
          <Checkbox
            checked={overwrite}
            onChange={(e) => setOverwrite(e.target.checked)}
            style={{ marginBottom: 12 }}
          >
            {t('ie.overwrite')}
          </Checkbox>
          <Divider />
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setMode('select')}>{t('common.back')}</Button>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              loading={loading}
              onClick={handleImport}
            >
              {t('common.import')} ({importData?.length || 0})
            </Button>
          </Space>
        </div>
      )}
    </Modal>
  );
}
