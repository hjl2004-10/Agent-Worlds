import { useState, useEffect } from 'react';
import {
  Space,
  Button,
  Typography,
  Input,
  message,
  Spin,
  Divider,
  Select,
  Tag,
} from 'antd';
import {
  GlobalOutlined,
  SaveOutlined,
  PlusOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { getLore, updateLore } from '@/api/god';
import { useWorldStore } from '@/store/useWorldStore';
import type { LoreData } from '@/api/types';
import { useT } from '@/i18n';

const { Text } = Typography;
const { TextArea } = Input;

export function LorePanel() {
  const t = useT();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lore, setLore] = useState<LoreData>({});

  // 世界状态
  const {
    currentWorld,
    currentScene,
    currentWorldInfo,
    availableWorlds,
    loading: worldLoading,
    fetchCurrentState,
    fetchAvailableWorlds,
    switchWorld,
    switchScene,
  } = useWorldStore();

  // 初始化
  useEffect(() => {
    fetchCurrentState();
    fetchAvailableWorlds();
  }, [fetchCurrentState, fetchAvailableWorlds]);

  // 加载当前世界的 lore
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const res = await getLore();
        if (res.data.status === 'ok') {
          setLore(res.data.lore || {});
        } else {
          message.error(t('lore.loadFailed'));
        }
      } catch (err) {
        message.error(t('lore.loadFailed'));
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [currentWorld]);

  // 保存世界观
  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await updateLore(lore);
      if (res.data.status === 'ok') {
        message.success(t('lore.saved'));
      } else {
        message.error(t('common.saveFailed'));
      }
    } catch (err) {
      message.error(t('common.saveFailed'));
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  // 切换世界
  const handleSwitchWorld = async (worldId: string) => {
    if (worldId === currentWorld) return;
    message.loading({ content: t('lore.switchingWorld'), key: 'switch' });
    await switchWorld(worldId);
  };

  const handleSwitchScene = async (sceneId: string) => {
    if (sceneId === currentScene) return;
    message.loading({ content: t('lore.switchingScene'), key: 'switch-scene' });
    await switchScene(sceneId);
  };

  // 更新规则
  const updateRule = (index: number, value: string) => {
    const newRules = [...(lore.rules || [])];
    newRules[index] = value;
    setLore({ ...lore, rules: newRules });
  };

  const addRule = () => {
    setLore({ ...lore, rules: [...(lore.rules || []), ''] });
  };

  const removeRule = (index: number) => {
    const newRules = [...(lore.rules || [])];
    newRules.splice(index, 1);
    setLore({ ...lore, rules: newRules });
  };

  // 更新历史
  const updateHistory = (index: number, value: string) => {
    const newHistory = [...(lore.history || [])];
    newHistory[index] = value;
    setLore({ ...lore, history: newHistory });
  };

  const addHistory = () => {
    setLore({ ...lore, history: [...(lore.history || []), ''] });
  };

  const removeHistory = (index: number) => {
    const newHistory = [...(lore.history || [])];
    newHistory.splice(index, 1);
    setLore({ ...lore, history: newHistory });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin />
      </div>
    );
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', paddingRight: 4 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 标题 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <GlobalOutlined style={{ color: '#38bdf8', fontSize: 18 }} />
            <Text strong style={{ color: 'var(--text-primary)' }}>{t('lore.title')}</Text>
          </Space>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            size="small"
            loading={saving}
            onClick={handleSave}
          >
            {t('common.save')}
          </Button>
        </div>

        {/* 世界切换 */}
        <div style={{
          background: 'var(--bg-panel)',
          borderRadius: 8,
          padding: 12,
          border: '1px solid var(--border-primary)'
        }}>
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>{t('lore.currentWorld')}</Text>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Select
              value={currentWorld}
              style={{ flex: 1 }}
              onChange={handleSwitchWorld}
              loading={worldLoading}
              options={availableWorlds.map(w => ({
                value: w.world_id,
                label: (
                  <Space>
                    <span>{w.display_name}</span>
                    <Tag color="blue" style={{ fontSize: 10 }}>{w.genre}</Tag>
                  </Space>
                ),
              }))}
            />
            <Tag color="green">{currentScene}</Tag>
          </div>
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {t('lore.switchWorldHint')}
            </Text>
          </div>
          {!!currentWorldInfo?.available_scenes?.length && (
            <div style={{ marginTop: 12 }}>
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>{t('lore.currentScene')}</Text>
              </div>
              <Select
                value={currentScene}
                style={{ width: '100%' }}
                onChange={handleSwitchScene}
                loading={worldLoading}
                options={currentWorldInfo.available_scenes.map(sceneId => ({
                  value: sceneId,
                  label: sceneId,
                }))}
              />
            </div>
          )}
        </div>

        <Divider style={{ margin: '8px 0', borderColor: 'var(--border-primary)' }} />

        {/* 世界名称 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
            {t('lore.worldName')}
          </Text>
          <Input
            value={lore.world_name || ''}
            onChange={(e) => setLore({ ...lore, world_name: e.target.value })}
            placeholder={t('lore.worldNamePlaceholder')}
            style={{ background: 'var(--bg-input)', borderColor: 'var(--border-primary)', color: 'var(--text-primary)' }}
          />
        </div>

        {/* 背景描述 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
            {t('lore.background')}
          </Text>
          <TextArea
            value={lore.background || ''}
            onChange={(e) => setLore({ ...lore, background: e.target.value })}
            placeholder={t('lore.backgroundPlaceholder')}
            rows={4}
            style={{ background: 'var(--bg-input)', borderColor: 'var(--border-primary)', color: 'var(--text-primary)' }}
          />
        </div>

        {/* 世界规则 */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('lore.rules')}
            </Text>
            <Button
              type="dashed"
              size="small"
              icon={<PlusOutlined />}
              onClick={addRule}
            >
              {t('common.add')}
            </Button>
          </div>
          <Space direction="vertical" style={{ width: '100%' }} size={4}>
            {(lore.rules || []).map((rule, index) => (
              <div key={index} style={{ display: 'flex', gap: 4 }}>
                <Input
                  value={rule}
                  onChange={(e) => updateRule(index, e.target.value)}
                  placeholder={`${t('lore.rulePlaceholder')} ${index + 1}`}
                  style={{ background: 'var(--bg-input)', borderColor: 'var(--border-primary)', color: 'var(--text-primary)', flex: 1 }}
                  size="small"
                />
                <Button
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => removeRule(index)}
                />
              </div>
            ))}
            {(lore.rules || []).length === 0 && (
              <Text type="secondary" style={{ fontSize: 11, fontStyle: 'italic' }}>
                {t('lore.noRules')}
              </Text>
            )}
          </Space>
        </div>

        {/* 历史事件 */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('lore.history')}
            </Text>
            <Button
              type="dashed"
              size="small"
              icon={<PlusOutlined />}
              onClick={addHistory}
            >
              {t('common.add')}
            </Button>
          </div>
          <Space direction="vertical" style={{ width: '100%' }} size={4}>
            {(lore.history || []).map((event, index) => (
              <div key={index} style={{ display: 'flex', gap: 4 }}>
                <Input
                  value={event}
                  onChange={(e) => updateHistory(index, e.target.value)}
                  placeholder={`${t('lore.eventPlaceholder')} ${index + 1}`}
                  style={{ background: 'var(--bg-input)', borderColor: 'var(--border-primary)', color: 'var(--text-primary)', flex: 1 }}
                  size="small"
                />
                <Button
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => removeHistory(index)}
                />
              </div>
            ))}
            {(lore.history || []).length === 0 && (
              <Text type="secondary" style={{ fontSize: 11, fontStyle: 'italic' }}>
                {t('lore.noHistory')}
              </Text>
            )}
          </Space>
        </div>
      </Space>
    </div>
  );
}
