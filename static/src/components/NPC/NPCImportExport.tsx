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

const { Text } = Typography;

interface NPCImportExportProps {
  open: boolean;
  onClose: () => void;
  npcs: NPC[];
  onSuccess: () => void;
}

export function NPCImportExport({ open, onClose, npcs, onSuccess }: NPCImportExportProps) {
  const [mode, setMode] = useState<'select' | 'export' | 'import'>('select');
  const [selectedNPCs, setSelectedNPCs] = useState<string[]>([]);
  const [overwrite, setOverwrite] = useState(false);
  const [loading, setLoading] = useState(false);
  const [importData, setImportData] = useState<NPCExportData[] | null>(null);
  const [importPreview, setImportPreview] = useState<{ name: string; exists: boolean }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExport = async () => {
    if (selectedNPCs.length === 0) {
      message.warning('请选择至少一个 NPC');
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

        message.success(`成功导出 ${data.exported_count} 个 NPC`);
        if (data.not_found && data.not_found.length > 0) {
          message.warning(`未找到: ${data.not_found.join(', ')}`);
        }
        handleClose();
      } else {
        message.error(data.message || '导出失败');
      }
    } catch (error) {
      message.error('导出失败');
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
          message.error('无效的文件格式');
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
        message.error('解析文件失败');
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
      message.warning('没有可导入的数据');
      return;
    }

    setLoading(true);
    try {
      const { data } = await importNPCs(importData, overwrite);
      if (data.status === 'ok') {
        message.success(`成功导入 ${data.imported_count} 个 NPC`);
        if (data.skipped && data.skipped.length > 0) {
          message.info(`已跳过 (已存在): ${data.skipped.join(', ')}`);
        }
        if (data.errors && data.errors.length > 0) {
          message.warning(`部分错误: ${data.errors.join(', ')}`);
        }
        onSuccess();
        handleClose();
      } else {
        message.error(data.message || '导入失败');
      }
    } catch (error) {
      message.error('导入失败');
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
          NPC 导入导出
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
            导出 NPC
          </Button>
          <Button
            icon={<ImportOutlined />}
            size="large"
            block
            onClick={() => fileInputRef.current?.click()}
          >
            导入 NPC
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
            <Text>选择要导出的 NPC：</Text>
            <Space>
              <Button size="small" onClick={selectAll}>
                全选
              </Button>
              <Button size="small" onClick={deselectAll}>
                取消全选
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
                      {npc.is_player && <Tag color="cyan">玩家</Tag>}
                      <Text type="secondary">({npc.x.toFixed(0)}, {npc.y.toFixed(0)})</Text>
                    </Space>
                  </Checkbox>
                </List.Item>
              )}
            />
          </div>
          <Divider />
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setMode('select')}>返回</Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              loading={loading}
              onClick={handleExport}
            >
              导出 ({selectedNPCs.length})
            </Button>
          </Space>
        </div>
      )}

      {mode === 'import' && (
        <div>
          <Alert
            message={`即将导入 ${importData?.length || 0} 个 NPC`}
            description="请确认导入列表，已存在的 NPC 将被跳过（除非勾选覆盖选项）"
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
                    {item.exists && <Tag color="orange">已存在</Tag>}
                    {!item.exists && <Tag color="green">新</Tag>}
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
            覆盖已存在的 NPC
          </Checkbox>
          <Divider />
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setMode('select')}>返回</Button>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              loading={loading}
              onClick={handleImport}
            >
              导入 ({importData?.length || 0})
            </Button>
          </Space>
        </div>
      )}
    </Modal>
  );
}
