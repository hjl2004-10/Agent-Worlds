import { useState, useEffect } from 'react';
import {
  Modal,
  Space,
  message,
  Typography,
  Spin,
} from 'antd';
import { getInventory } from '@/api/god';

const { Text } = Typography;

interface InventoryPanelProps {
  npcName: string | null;
  open: boolean;
  onClose: () => void;
}

interface AttrSchema {
  visibility?: string;
  writable_by_owner?: boolean;
  requires_auth?: boolean;
  description?: string;
}

interface InventoryData {
  schema: Record<string, AttrSchema>;
  inventory: Record<string, string | number>;
}

const ATTR_COLORS = ['#4ade80', '#38bdf8', '#e879f9', '#fbbf24', '#f87171', '#a78bfa', '#fb7185'];

export function InventoryPanel({ npcName, open, onClose }: InventoryPanelProps) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<InventoryData>({ schema: {}, inventory: {} });
  const [selectedAttr, setSelectedAttr] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !npcName) return;

    const loadData = async () => {
      setLoading(true);
      setSelectedAttr(null);
      try {
        const res = await getInventory(npcName);
        if (res.data.status === 'ok') {
          setData({
            schema: res.data.schema || {},
            inventory: res.data.inventory || {},
          });
        } else {
          message.error(res.data.message || '加载背包数据失败');
        }
      } catch (err) {
        message.error('加载背包数据失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [open, npcName]);

  const getAttrColor = (index: number) => ATTR_COLORS[index % ATTR_COLORS.length];

  const selectedSchema = selectedAttr ? data.schema[selectedAttr] : null;
  const selectedValue = selectedAttr ? data.inventory[selectedAttr] : null;

  const attrKeys = Object.keys(data.schema);
  const emptySlots = Math.max(0, 8 - attrKeys.length);

  return (
    <Modal
      title={
        <Space>
          <img
            src="/ui/inv-icon-bag.png"
            alt="bag"
            style={{ width: 20, height: 18, imageRendering: 'pixelated' }}
          />
          <span>{npcName} 的背包</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={440}
      centered
      styles={{
        content: { background: 'var(--bg-panel)', border: '2px solid var(--border-accent)' },
        header: { background: 'var(--bg-panel)', borderBottom: '1px solid #2a3a3a' },
        body: { padding: 14 },
      }}
      footer={null}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : (
        <>
          {/* 背包网格 */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 6,
          }}>
            {attrKeys.map((key, index) => {
              const isSelected = selectedAttr === key;
              const color = getAttrColor(index);

              return (
                <div
                  key={key}
                  className={`pixel-slot ${isSelected ? 'pixel-slot--selected' : 'pixel-slot--normal'}`}
                  onClick={() => setSelectedAttr(isSelected ? null : key)}
                >
                  <div className="pixel-slot__name" style={{ color }}>
                    {key}
                  </div>
                  <div className="pixel-slot__value">
                    {data.inventory[key] ?? '-'}
                  </div>
                </div>
              );
            })}

            {/* 空格子 */}
            {Array.from({ length: emptySlots }).map((_, i) => (
              <div
                key={`empty-${i}`}
                className="pixel-slot pixel-slot--empty"
              />
            ))}
          </div>

          {/* 选中属性详情 */}
          {selectedAttr && selectedSchema && (
            <div className="inv-detail-panel">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <Text strong style={{ color: 'var(--text-primary)', fontSize: 14 }}>{selectedAttr}</Text>
                <Text style={{ color: '#fbbf24', fontSize: 18, fontWeight: 'bold', fontFamily: 'monospace' }}>
                  {selectedValue ?? '-'}
                </Text>
              </div>
              {selectedSchema.description ? (
                <Text style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                  {selectedSchema.description}
                </Text>
              ) : (
                <Text style={{ color: 'var(--text-muted)', fontSize: 12, fontStyle: 'italic' }}>
                  暂无描述
                </Text>
              )}
            </div>
          )}

          {/* 空状态 */}
          {attrKeys.length === 0 && (
            <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)' }}>
              背包空空如也
            </div>
          )}
        </>
      )}
    </Modal>
  );
}
