import { Typography, InputNumber, Space, Slider, Tooltip, Switch } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface BehaviorConfigProps {
  baseInitiative: number;
  walkIdle: number;
  walkRandom: number;
  walkLinear: number;
  noCollision?: boolean;
  onChange: (behavior: {
    base_initiative?: number;
    walk_idle?: number;
    walk_random?: number;
    walk_linear?: number;
    no_collision?: boolean;
  }) => void;
  disabled?: boolean;
}

export function BehaviorConfig({ baseInitiative, walkIdle, walkRandom, walkLinear, noCollision, onChange, disabled }: BehaviorConfigProps) {
  // 计算总时间用于可视化
  const total = (walkIdle || 0) + (walkRandom || 0) + (walkLinear || 0);

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 基础主动值 */}
        <div>
          <Space style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>基础主动值</Text>
            <Tooltip title="NPC 主动发起对话的基础概率，范围 0-10">
              <InfoCircleOutlined style={{ color: 'var(--text-icon-muted)', fontSize: 12 }} />
            </Tooltip>
          </Space>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <Slider
                min={0}
                max={10}
                step={1}
                value={baseInitiative}
                onChange={(value) => onChange({ base_initiative: value })}
                disabled={disabled}
                marks={{
                  0: '沉默',
                  5: '正常',
                  10: '话唠',
                }}
              />
            </div>
            <InputNumber
              min={0}
              max={10}
              value={baseInitiative}
              onChange={(value) => onChange({ base_initiative: value ?? 0 })}
              disabled={disabled}
              style={{ width: 60 }}
            />
          </div>
        </div>

        {/* 行走模式配比 (三态循环: idle -> random -> linear -> idle) */}
        <div>
          <Space style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>行走模式配比</Text>
            <Tooltip title="三态循环: 静默 -> 随机漫步 -> 直线行走 -> 静默">
              <InfoCircleOutlined style={{ color: 'var(--text-icon-muted)', fontSize: 12 }} />
            </Tooltip>
          </Space>

          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ marginBottom: 4 }}>
                <Text style={{ fontSize: 11, color: 'var(--text-secondary)' }}>静默</Text>
              </div>
              <InputNumber
                min={0}
                max={300}
                value={walkIdle}
                onChange={(value) => onChange({ walk_idle: value ?? 0 })}
                disabled={disabled}
                addonAfter="ticks"
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ marginBottom: 4 }}>
                <Text style={{ fontSize: 11, color: '#4ade80' }}>随机</Text>
              </div>
              <InputNumber
                min={0}
                max={200}
                value={walkRandom}
                onChange={(value) => onChange({ walk_random: value ?? 0 })}
                disabled={disabled}
                addonAfter="ticks"
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ marginBottom: 4 }}>
                <Text style={{ fontSize: 11, color: '#38bdf8' }}>直线</Text>
              </div>
              <InputNumber
                min={0}
                max={200}
                value={walkLinear}
                onChange={(value) => onChange({ walk_linear: value ?? 0 })}
                disabled={disabled}
                addonAfter="ticks"
                style={{ width: '100%' }}
              />
            </div>
          </div>

          {/* 可视化配比 (三色条) */}
          {total > 0 && (
            <div style={{ marginTop: 8 }}>
              <div
                style={{
                  height: 8,
                  borderRadius: 4,
                  background: `linear-gradient(to right,
                    #9ca3af 0%,
                    #9ca3af ${(walkIdle / total) * 100}%,
                    #4ade80 ${(walkIdle / total) * 100}%,
                    #4ade80 ${((walkIdle + walkRandom) / total) * 100}%,
                    #38bdf8 ${((walkIdle + walkRandom) / total) * 100}%
                  )`,
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                <Text type="secondary" style={{ fontSize: 10 }}>静默</Text>
                <Text type="secondary" style={{ fontSize: 10 }}>随机</Text>
                <Text type="secondary" style={{ fontSize: 10 }}>直线</Text>
              </div>
            </div>
          )}
        </div>

        {/* 快速预设 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
            快速预设
          </Text>
          <Space wrap>
            <BehaviorPresetButton
              label="活泼好动"
              values={{ base_initiative: 8, walk_idle: 20, walk_random: 40, walk_linear: 40 }}
              current={{ baseInitiative, walkIdle, walkRandom, walkLinear }}
              onClick={onChange}
              disabled={disabled}
            />
            <BehaviorPresetButton
              label="安静内向"
              values={{ base_initiative: 2, walk_idle: 100, walk_random: 20, walk_linear: 30 }}
              current={{ baseInitiative, walkIdle, walkRandom, walkLinear }}
              onClick={onChange}
              disabled={disabled}
            />
            <BehaviorPresetButton
              label="均衡型"
              values={{ base_initiative: 5, walk_idle: 50, walk_random: 30, walk_linear: 40 }}
              current={{ baseInitiative, walkIdle, walkRandom, walkLinear }}
              onClick={onChange}
              disabled={disabled}
            />
            <BehaviorPresetButton
              label="爱到处跑"
              values={{ base_initiative: 6, walk_idle: 10, walk_random: 50, walk_linear: 60 }}
              current={{ baseInitiative, walkIdle, walkRandom, walkLinear }}
              onClick={onChange}
              disabled={disabled}
            />
          </Space>
        </div>

        {/* 碰撞设置 */}
        <div>
          <Space style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>禁用碰撞对话</Text>
            <Tooltip title="开启后 NPC 不会因碰撞触发对话，但仍会物理重叠">
              <InfoCircleOutlined style={{ color: 'var(--text-icon-muted)', fontSize: 12 }} />
            </Tooltip>
          </Space>
          <div>
            <Switch
              checked={noCollision}
              onChange={(checked) => onChange({ no_collision: checked })}
              disabled={disabled}
              checkedChildren="禁用"
              unCheckedChildren="启用"
            />
          </div>
        </div>
      </Space>
    </div>
  );
}

// 预设按钮组件
interface BehaviorPresetButtonProps {
  label: string;
  values: { base_initiative: number; walk_idle: number; walk_random: number; walk_linear: number };
  current: { baseInitiative: number; walkIdle: number; walkRandom: number; walkLinear: number };
  onClick: (values: { base_initiative: number; walk_idle: number; walk_random: number; walk_linear: number }) => void;
  disabled?: boolean;
}

function BehaviorPresetButton({ label, values, current, onClick, disabled }: BehaviorPresetButtonProps) {
  const isActive =
    current.baseInitiative === values.base_initiative &&
    current.walkIdle === values.walk_idle &&
    current.walkRandom === values.walk_random &&
    current.walkLinear === values.walk_linear;

  return (
    <button
      onClick={() => onClick(values)}
      disabled={disabled}
      style={{
        padding: '4px 12px',
        borderRadius: 4,
        border: isActive ? '1px solid #4ade80' : '1px solid var(--border-accent)',
        background: isActive ? 'rgba(74, 222, 128, 0.1)' : 'var(--bg-hover)',
        color: isActive ? '#4ade80' : 'var(--text-primary)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontSize: 12,
      }}
    >
      {label}
    </button>
  );
}
