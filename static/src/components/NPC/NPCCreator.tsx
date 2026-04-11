import { useState, useEffect } from 'react';
import {
  Modal,
  Steps,
  Input,
  Select,
  InputNumber,
  Button,
  Space,
  Typography,
  message,
  Result,
  Divider,
  Tag,
  Row,
  Col,
  Checkbox,
} from 'antd';
import {
  UserOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  PictureOutlined,
} from '@ant-design/icons';
import { createNPC, getLLMChannels, getSprites } from '@/api/god';
import { spriteIdsToOptions } from '@/config/sprites';
import { ModelConfig } from './ModelConfig';
import { BehaviorConfig } from './BehaviorConfig';
import type { LLMChannel, NPCCreateRequest } from '@/api/types';
import { useT } from '@/i18n';

const { Text, Title } = Typography;

interface NPCCreatorProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

// 默认提示词模板
const DEFAULT_PROMPT_TEMPLATE = [
  '当前时间: {time_str} ({period})',
  '{persona}',
  '你正在和 {listener_name} 对话。{relation_desc}',
  '{tools_prompt}',
  '{extra_prompt}',
  '{tasks_text}',
  '{task_tools_text}',
  '[你的记忆]:\n{memory_text}',
];

export function NPCCreator({ open, onClose, onSuccess }: NPCCreatorProps) {
  const t = useT();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [sprites, setSprites] = useState<string[]>([]);
  const [_channels, setChannels] = useState<LLMChannel[]>([]);
  const [defaultChannel, setDefaultChannel] = useState('');

  // 表单数据
  const [formData, setFormData] = useState<NPCCreateRequest>({
    name: '',
    sprite_id: 'Adam',
    description: '',
    x: 100,
    y: 100,
    prompt: DEFAULT_PROMPT_TEMPLATE,
    extra_prompt: '',
    tools: [],
    groups: [],
      llm: { channel: undefined, model: undefined },
    behavior: { base_initiative: 5, walk_idle: 80, walk_random: 30, walk_linear: 20 },
    is_player: false,
  });

  // 创建结果
  const [created, setCreated] = useState<{ name: string; success: boolean } | null>(null);

  // 加载精灵和渠道列表
  useEffect(() => {
    if (!open) return;

    const loadData = async () => {
      try {
        const [spritesRes, channelsRes] = await Promise.all([
          getSprites(),
          getLLMChannels(),
        ]);

        if (spritesRes.data.status === 'ok') {
          setSprites(spritesRes.data.sprites);
        }

        if (channelsRes.data.status === 'ok') {
          setChannels(channelsRes.data.channels);
          setDefaultChannel(channelsRes.data.default_channel);
        }
      } catch (err) {
        console.error('Load data failed:', err);
      }
    };

    loadData();
  }, [open]);

  // 重置表单
  const resetForm = () => {
    setCurrentStep(0);
    setCreated(null);
    setFormData({
      name: '',
      sprite_id: 'Adam',
      description: '',
      x: 100,
      y: 100,
      prompt: DEFAULT_PROMPT_TEMPLATE,
      extra_prompt: '',
      tools: [],
      groups: [],
            llm: { channel: undefined, model: undefined },
      behavior: { base_initiative: 5, walk_idle: 80, walk_random: 30, walk_linear: 20 },
      is_player: false,
    });
  };

  // 关闭时重置
  const handleClose = () => {
    resetForm();
    onClose();
  };

  // 下一步
  const handleNext = () => {
    // 验证当前步骤
    if (currentStep === 0) {
      if (!formData.name.trim()) {
        message.error(t('creator.warnName'));
        return;
      }
      if (!/^[a-zA-Z\u4e00-\u9fa5]+$/.test(formData.name)) {
        message.error(t('creator.warnNameFormat'));
        return;
      }
    }
    setCurrentStep(currentStep + 1);
  };

  // 上一步
  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  // 创建 NPC
  const handleCreate = async () => {
    setLoading(true);
    try {
      const res = await createNPC(formData);
      if (res.data.status === 'ok') {
        setCreated({ name: formData.name, success: true });
        onSuccess?.();
      } else {
        message.error(res.data.message || t('creator.createFailed'));
        setCreated({ name: formData.name, success: false });
      }
    } catch (err) {
      message.error(t('creator.createFailed'));
      console.error(err);
      setCreated({ name: formData.name, success: false });
    } finally {
      setLoading(false);
    }
  };

  // 更新表单字段
  const updateField = <K extends keyof NPCCreateRequest>(key: K, value: NPCCreateRequest[K]) => {
    setFormData({ ...formData, [key]: value });
  };

  // 步骤配置
  const steps = [
    {
      title: t('creator.step.basic'),
      icon: <UserOutlined />,
      content: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 名称 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              {t('creator.npcName')} <Text type="danger">*</Text>
            </Text>
            <Input
              value={formData.name}
              onChange={(e) => updateField('name', e.target.value)}
              placeholder={t('creator.npcNamePlaceholder')}
              size="large"
            />
          </div>

          {/* 精灵 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              <PictureOutlined /> {t('config.sprite')}
            </Text>
            <Select
              value={formData.sprite_id}
              onChange={(value) => {
                // 忽略分组标题点击
                if (value.startsWith('__group_')) return;
                updateField('sprite_id', value);
              }}
              style={{ width: '100%' }}
              options={spriteIdsToOptions(sprites)}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </div>

          {/* 初始位置 */}
          <Row gutter={16}>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                {t('creator.xCoord')}
              </Text>
              <InputNumber
                value={formData.x}
                onChange={(value) => updateField('x', value ?? 0)}
                min={0}
                max={500}
                style={{ width: '100%' }}
              />
            </Col>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                {t('creator.yCoord')}
              </Text>
              <InputNumber
                value={formData.y}
                onChange={(value) => updateField('y', value ?? 0)}
                min={0}
                max={500}
                style={{ width: '100%' }}
              />
            </Col>
          </Row>

          {/* 玩家标识 */}
          <div>
            <Checkbox
              checked={formData.is_player}
              onChange={(e) => updateField('is_player', e.target.checked)}
            >
              {t('creator.isPlayer')}
            </Checkbox>
          </div>
        </Space>
      ),
    },
    {
      title: t('creator.step.persona'),
      icon: <RobotOutlined />,
      content: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              {t('creator.persona')}
            </Text>
            <Input.TextArea
              value={formData.description}
              onChange={(e) => updateField('description', e.target.value)}
              placeholder={t('creator.personaPlaceholder')}
              rows={5}
              style={{ background: 'var(--bg-panel)', color: 'var(--text-white)' }}
            />
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              {t('creator.extraPrompt')}
            </Text>
            <Input.TextArea
              value={formData.extra_prompt}
              onChange={(e) => updateField('extra_prompt', e.target.value)}
              placeholder={t('creator.extraPromptPlaceholder')}
              rows={2}
              style={{ background: 'var(--bg-panel)', color: 'var(--text-white)' }}
            />
          </div>
        </Space>
      ),
    },
    {
      title: t('creator.step.model'),
      icon: <RobotOutlined />,
      content: (
        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
            {t('creator.modelHint')}
          </Text>
          <ModelConfig
            channel={formData.llm?.channel || null}
            model={formData.llm?.model || null}
                      onChange={({ channel, model }) => {
              updateField('llm', { channel: channel ?? undefined, model: model ?? undefined });
            }}
          />
        </div>
      ),
    },
    {
      title: t('creator.step.behavior'),
      icon: <ThunderboltOutlined />,
      content: (
        <BehaviorConfig
          baseInitiative={formData.behavior?.base_initiative || 5}
          walkIdle={formData.behavior?.walk_idle || 80}
          walkRandom={formData.behavior?.walk_random || 30}
          walkLinear={formData.behavior?.walk_linear || 20}
          noCollision={formData.behavior?.no_collision || false}
          onChange={(behavior) => {
            updateField('behavior', {
              ...formData.behavior,
              ...behavior,
            });
          }}
        />
      ),
    },
    {
      title: t('creator.step.confirm'),
      icon: <CheckCircleOutlined />,
      content: created ? (
        <Result
          status={created.success ? 'success' : 'error'}
          title={created.success ? t('creator.createSuccess') : t('creator.createFailed')}
          subTitle={created.success ? `NPC "${created.name}" ${t('creator.createSuccessDesc')}` : t('creator.createFailedDesc')}
          extra={
            created.success && (
              <Button type="primary" onClick={handleClose}>
                {t('god.done')}
              </Button>
            )
          }
        />
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <Title level={5}>{t('creator.confirmTitle')}: {formData.name}</Title>
          <Divider style={{ margin: '12px 0' }} />

          <Row gutter={[8, 8]}>
            <Col span={8}><Text type="secondary">{t('creator.spriteLabel')}</Text></Col>
            <Col span={16}><Tag>{formData.sprite_id}</Tag></Col>

            <Col span={8}><Text type="secondary">{t('creator.posLabel')}</Text></Col>
            <Col span={16}><Text>({formData.x}, {formData.y})</Text></Col>

            <Col span={8}><Text type="secondary">{t('creator.typeLabel')}</Text></Col>
            <Col span={16}>
              <Tag color={formData.is_player ? 'cyan' : 'default'}>
                {formData.is_player ? t('npc.status.player') : 'NPC'}
              </Tag>
            </Col>

            <Col span={8}><Text type="secondary">{t('creator.llmLabel')}</Text></Col>
            <Col span={16}>
              <Text>
                {formData.llm?.channel || defaultChannel || t('creator.default')}
                {formData.llm?.model && ` / ${formData.llm.model}`}
              </Text>
            </Col>

            <Col span={8}><Text type="secondary">{t('creator.initiativeLabel')}</Text></Col>
            <Col span={16}><Text>{formData.behavior?.base_initiative || 5}</Text></Col>

            <Col span={24}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t('creator.personaLabel')} {formData.description || t('creator.notSet')}
              </Text>
            </Col>
          </Row>
        </Space>
      ),
    },
  ];

  return (
    <Modal
      title={t('creator.title')}
      open={open}
      onCancel={handleClose}
      width={600}
      footer={null}
      destroyOnClose
    >
      <Steps
        current={currentStep}
        size="small"
        items={steps.map(s => ({ title: s.title, icon: s.icon }))}
        style={{ marginBottom: 24 }}
      />

      <div style={{ minHeight: 280, marginBottom: 24 }}>
        {steps[currentStep].content}
      </div>

      {/* 底部按钮 */}
      {!created && (
        <div style={{ textAlign: 'right' }}>
          <Space>
            {currentStep > 0 && (
              <Button onClick={handlePrev}>{t('creator.prev')}</Button>
            )}
            {currentStep < steps.length - 1 ? (
              <Button type="primary" onClick={handleNext}>
                {t('creator.next')}
              </Button>
            ) : (
              <Button type="primary" loading={loading} onClick={handleCreate}>
                {t('common.create')}
              </Button>
            )}
          </Space>
        </div>
      )}
    </Modal>
  );
}
