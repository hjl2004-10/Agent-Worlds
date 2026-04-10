import { useState } from 'react';
import { Input, Typography, Space, Button, Collapse, Tag, Tooltip } from 'antd';
import { PlusOutlined, DeleteOutlined, InfoCircleOutlined } from '@ant-design/icons';

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
const PROMPT_VARIABLES = [
  { name: 'time_str', desc: '当前时间 (如 08:30)' },
  { name: 'period', desc: '时间段 (如 早晨、下午)' },
  { name: 'persona', desc: 'NPC 人设描述' },
  { name: 'listener_name', desc: '对话对象名称' },
  { name: 'speaker_name', desc: 'NPC 自己的名称' },
  { name: 'relation_desc', desc: '与对话对象的关系描述' },
  { name: 'lore_text', desc: '世界观 + 场景描述' },
  { name: 'scene_name', desc: '当前场景名称' },
  { name: 'scene_desc', desc: '当前场景描述' },
  { name: 'tools_prompt', desc: '工具提示 (Skill/MCP 动态生成)' },
  { name: 'extra_prompt', desc: '额外提示 (用户手写的指令)' },
  { name: 'tasks_text', desc: '当前任务列表' },
  { name: 'task_tools_text', desc: '任务动态工具提示' },
  { name: 'memory_text', desc: '历史记忆 (按相关性筛选)' },
  { name: 'memory_note', desc: 'NPC 笔记 (手动编辑的备忘)' },
];

export function PromptConfig({ description, prompt, extraPrompt, onChange, disabled }: PromptConfigProps) {
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
              <Text>人设描述</Text>
              {description && <Tag color="green">已设置</Tag>}
            </Space>
          }
          key="description"
          style={{ background: 'var(--bg-input)' }}
        >
          <TextArea
            value={description}
            onChange={handleDescriptionChange}
            placeholder="描述 NPC 的性格、背景、说话风格等..."
            rows={4}
            disabled={disabled}
            style={{ background: 'var(--bg-panel)', color: 'var(--text-white)' }}
          />
        </Panel>

        {/* 提示词模板 */}
        <Panel
          header={
            <Space>
              <Text>提示词模板</Text>
              <Tooltip title="系统提示词的模板数组，将按顺序拼接">
                <InfoCircleOutlined style={{ color: 'var(--text-icon-muted)' }} />
              </Tooltip>
              {prompt.length > 0 && <Tag color="blue">{prompt.length} 项</Tag>}
            </Space>
          }
          key="prompt"
          style={{ background: 'var(--bg-input)' }}
        >
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {/* 可用变量提示 */}
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>可用变量: </Text>
              {PROMPT_VARIABLES.map(v => (
                <Tooltip key={v.name} title={v.desc}>
                  <Tag style={{ fontSize: 10, margin: '2px', cursor: 'help' }}>
                    {'{'}{v.name}{'}'}
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
                  placeholder={`提示词模板第 ${index + 1} 行...`}
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
              添加模板项
            </Button>
          </Space>
        </Panel>

        {/* 额外提示 */}
        <Panel
          header={
            <Space>
              <Text>额外提示</Text>
              <Tooltip title="用户手写的额外指令/教学提示词，独立于 Skill/MCP 自动生成的工具描述">
                <InfoCircleOutlined style={{ color: 'var(--text-icon-muted)' }} />
              </Tooltip>
              {extraPrompt && <Tag color="purple">已设置</Tag>}
            </Space>
          }
          key="extraPrompt"
          style={{ background: 'var(--bg-input)' }}
        >
          <TextArea
            value={extraPrompt}
            onChange={handleExtraPromptChange}
            placeholder="例如: 当你觉得和对方成为朋友时，输出[group:朋友]。"
            rows={3}
            disabled={disabled}
            style={{ background: 'var(--bg-panel)', color: 'var(--text-white)' }}
          />
        </Panel>
      </Collapse>
    </div>
  );
}
