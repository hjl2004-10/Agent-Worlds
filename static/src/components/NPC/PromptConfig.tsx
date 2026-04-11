import { useState } from 'react';
import { Input, Typography, Space, Button, Collapse, Tag, Tooltip } from 'antd';
import { PlusOutlined, DeleteOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useT } from '@/i18n';

const { TextArea } = Input;
const { Text } = Typography;
const { Panel } = Collapse;

interface PromptConfigProps {
  description: string;
  prompt: string[];
  extraPrompt: string;
  onChange: (data: {
    description?: string;
    prompt?: string[];
    extraPrompt?: string;
  }) => void;
  disabled?: boolean;
}

// 可用的提示词变量 (与 prompt_l2.build_context 一一对应)
const PROMPT_VARIABLE_NAMES = [
  'time_str', 'period', 'persona', 'listener_name', 'speaker_name',
  'relation_desc', 'lore_text', 'scene_name', 'scene_desc',
  'tools_prompt', 'extra_prompt', 'tasks_text', 'task_tools_text',
  'memory_text', 'memory_note',
];

export function PromptConfig({ description, prompt, extraPrompt, onChange, disabled }: PromptConfigProps) {
  const t = useT();
  const [activeKey, setActiveKey] = useState<string[]>(['description']);

  // 更新人设
  const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({ description: e.target.value });
  };

  // 更新额外提示
  const handleExtraPromptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({ extraPrompt: e.target.value });
  };

  // 更新提示词模板项
  const handlePromptItemChange = (index: number, value: string) => {
    const newPrompt = [...prompt];
    newPrompt[index] = value;
    onChange({ prompt: newPrompt });
  };

  // 添加提示词模板项
  const handleAddPromptItem = () => {
    onChange({ prompt: [...prompt, ''] });
  };

  // 删除提示词模板项
  const handleRemovePromptItem = (index: number) => {
    const newPrompt = prompt.filter((_, i) => i !== index);
    onChange({ prompt: newPrompt });
  };

  return (
    <div>
      <Collapse
        activeKey={activeKey}
        onChange={(keys) => setActiveKey(keys as string[])}
        style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-primary)' }}
      >
        {/* 人设描述 */}
        <Panel
          header={
            <Space>
              <Text>{t('prompt.description')}</Text>
              {description && <Tag color="green">{t('prompt.descSet')}</Tag>}
            </Space>
          }
          key="description"
          style={{ background: 'var(--bg-input)' }}
        >
          <TextArea
            value={description}
            onChange={handleDescriptionChange}
            placeholder={t('prompt.descPlaceholder')}
            rows={4}
            disabled={disabled}
            style={{ background: 'var(--bg-panel)', color: 'var(--text-white)' }}
          />
        </Panel>

        {/* 提示词模板 */}
        <Panel
          header={
            <Space>
              <Text>{t('prompt.template')}</Text>
              <Tooltip title={t('prompt.templateTip')}>
                <InfoCircleOutlined style={{ color: 'var(--text-icon-muted)' }} />
              </Tooltip>
              {prompt.length > 0 && <Tag color="blue">{prompt.length} {t('prompt.items')}</Tag>}
            </Space>
          }
          key="prompt"
          style={{ background: 'var(--bg-input)' }}
        >
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {/* 可用变量提示 */}
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>{t('prompt.variables')}</Text>
              {PROMPT_VARIABLE_NAMES.map(name => (
                <Tooltip key={name} title={t(`prompt.varDesc.${name}`)}>
                  <Tag style={{ fontSize: 10, margin: '2px', cursor: 'help' }}>
                    {'{'}{name}{'}'}
                  </Tag>
                </Tooltip>
              ))}
            </div>

            {/* 模板项列表 */}
            {prompt.map((item, index) => (
              <div key={index} style={{ display: 'flex', gap: 8 }}>
                <Tag style={{ minWidth: 24, textAlign: 'center' }}>{index + 1}</Tag>
                <TextArea
                  value={item}
                  onChange={(e) => handlePromptItemChange(index, e.target.value)}
                  placeholder={t('prompt.itemPlaceholder').replace('{n}', String(index + 1))}
                  rows={2}
                  disabled={disabled}
                  style={{ flex: 1, background: 'var(--bg-panel)', color: 'var(--text-white)' }}
                />
                <Button
                  icon={<DeleteOutlined />}
                  danger
                  disabled={disabled}
                  onClick={() => handleRemovePromptItem(index)}
                />
              </div>
            ))}

            {/* 添加按钮 */}
            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={handleAddPromptItem}
              disabled={disabled}
              style={{ width: '100%' }}
            >
              {t('prompt.addItem')}
            </Button>
          </Space>
        </Panel>

        {/* 额外提示 */}
        <Panel
          header={
            <Space>
              <Text>{t('prompt.extra')}</Text>
              <Tooltip title={t('prompt.extraTip')}>
                <InfoCircleOutlined style={{ color: 'var(--text-icon-muted)' }} />
              </Tooltip>
              {extraPrompt && <Tag color="purple">{t('prompt.descSet')}</Tag>}
            </Space>
          }
          key="extraPrompt"
          style={{ background: 'var(--bg-input)' }}
        >
          <TextArea
            value={extraPrompt}
            onChange={handleExtraPromptChange}
            placeholder={t('prompt.extraPlaceholder')}
            rows={3}
            disabled={disabled}
            style={{ background: 'var(--bg-panel)', color: 'var(--text-white)' }}
          />
        </Panel>
      </Collapse>
    </div>
  );
}
