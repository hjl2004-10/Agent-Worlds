/**
 * SettingsPanel - 设置面板
 *
 * 背景图切换、缩放控制等设置
 */
import { Slider } from 'antd';
import { BACKGROUNDS } from './VirtualComputer';

interface SettingsPanelProps {
  backgroundId: string;
  onBackgroundChange: (id: string) => void;
  scale: number;
  onScaleChange: (scale: number) => void;
  onClose: () => void;
}

export function SettingsPanel({
  backgroundId,
  onBackgroundChange,
  scale,
  onScaleChange,
  onClose
}: SettingsPanelProps) {
  return (
    <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
      <div className="settings-header">
        <h3>⚙️ 设置</h3>
        <button className="settings-close" onClick={onClose}>
          ×
        </button>
      </div>

      {/* 缩放控制 */}
      <div className="settings-section">
        <h4>缩放比例</h4>
        <div style={{ padding: '0 8px' }}>
          <Slider
            min={30}
            max={200}
            value={Math.round(scale * 100)}
            onChange={(v) => onScaleChange(v / 100)}
            marks={{
              30: '30%',
              50: '50%',
              100: '100%',
              150: '150%',
              200: '200%',
            }}
            tooltip={{ formatter: (v) => `${v}%` }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 8 }}>
          <button
            className="zoom-btn"
            onClick={() => onScaleChange(Math.max(0.3, scale / 1.2))}
          >
            - 缩小
          </button>
          <button
            className="zoom-btn"
            onClick={() => onScaleChange(1)}
          >
            重置
          </button>
          <button
            className="zoom-btn"
            onClick={() => onScaleChange(Math.min(2, scale * 1.2))}
          >
            + 放大
          </button>
        </div>
      </div>

      {/* 背景主题 */}
      <div className="settings-section">
        <h4>背景主题</h4>
        <div className="background-grid">
          {BACKGROUNDS.map((bg) => (
            <div
              key={bg.id}
              className={`background-option ${backgroundId === bg.id ? 'active' : ''}`}
              onClick={() => onBackgroundChange(bg.id)}
            >
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  background: bg.color,
                  borderRadius: 6,
                }}
              />
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
          {BACKGROUNDS.map((bg) => (
            <span
              key={bg.id}
              style={{
                fontSize: 10,
                color: backgroundId === bg.id ? '#1890ff' : '#666',
                width: '33%',
                textAlign: 'center',
              }}
            >
              {bg.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
