/**
 * PendingManager - 待归一实体管理
 *
 * 列出 pending entity (陌生新名), 每个可:
 *   - 归并到已有 entity (填 entity_id, 别名迁移+关系改指+删pending)
 *   - 转正式 (确认是新实体, pending=false)
 * 操作后刷新。
 */
import { useState, useEffect } from 'react';
import { List, Button, Input, Tag, Typography, Space, Empty, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { graphApi } from '@/api/god';

const { Text } = Typography;

export function PendingManager() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [mergeInputs, setMergeInputs] = useState<Record<string, string>>({});

  const fetchPending = async () => {
    setLoading(true);
    try {
      const { data } = await graphApi.getPending();
      if (data.status === 'ok') setItems(data.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  const resolve = async (id: string, worldId: string, mergeTo?: string) => {
    const { data } = await graphApi.resolvePending(id, worldId, mergeTo);
    if (data.status === 'ok') {
      message.success(mergeTo ? `已归并到 ${mergeTo}` : `${id} 已转正式`);
      setMergeInputs((m) => ({ ...m, [id]: '' }));
      fetchPending();
    } else {
      message.error('操作失败');
    }
  };

  return (
    <div style={{ height: '64vh', display: 'flex', flexDirection: 'column' }}>
      <Space style={{ marginBottom: 8 }}>
        <Text strong>待归一实体（{items.length}）</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          陌生新名待确认：是某个已有实体的别名（归并），还是独立新实体（转正式）
        </Text>
        <Button size="small" icon={<ReloadOutlined />} onClick={fetchPending} loading={loading}>
          刷新
        </Button>
      </Space>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {items.length === 0 ? (
          <div style={{ paddingTop: 80 }}>
            <Empty description="没有待归一实体" />
          </div>
        ) : (
          <List
            dataSource={items}
            renderItem={(it: any) => (
              <List.Item>
                <Space wrap>
                  <Tag color="orange" style={{ fontSize: 14 }}>{it.id}</Tag>
                  <Tag>{it.world_id}</Tag>
                  <Input.Search
                    placeholder="归并到 entity_id (如 boss)"
                    size="small"
                    style={{ width: 220 }}
                    value={mergeInputs[it.id] || ''}
                    onChange={(e) => setMergeInputs((m) => ({ ...m, [it.id]: e.target.value }))}
                    enterButton="归并"
                    onSearch={(v) => {
                      const t = v.trim();
                      if (t) resolve(it.id, it.world_id, t);
                    }}
                  />
                  <Button size="small" onClick={() => resolve(it.id, it.world_id)}>
                    转正式
                  </Button>
                </Space>
              </List.Item>
            )}
          />
        )}
      </div>
    </div>
  );
}
