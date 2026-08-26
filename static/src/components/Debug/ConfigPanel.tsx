/**
 * ConfigPanel - 运行时配置面板 (记忆 + 图谱 limit)
 *
 * memory: relevant/other limit, 注入对方简介, 相关性过滤
 * graph: 共同事件/关系网条数, 图谱文本上限, 描述截断, 显示关系网概览
 * 保存即时生效 (后端 set_prompt_config/graph.set_config + 持久化)
 */
import { useState, useEffect } from 'react';
import { Form, InputNumber, Switch, Button, Typography, message, Spin, Divider } from 'antd';
import { configApi } from '@/api/god';

const { Title, Text } = Typography;

export function ConfigPanel() {
  const [memory, setMemory] = useState<any>(null);
  const [graph, setGraph] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchCfg = async () => {
    setLoading(true);
    try {
      const { data } = await configApi.get();
      if (data.status === 'ok') {
        setMemory(data.memory);
        setGraph(data.graph);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCfg();
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const m = { ...memory };
      const g = { ...graph };
      delete m._comment;
      delete g._comment;
      delete g.uri; delete g.user; delete g.password; delete g.enabled;  // 不改连接配置
      const { data } = await configApi.set(m, g);
      if (data.status === 'ok') {
        setMemory(data.memory);
        setGraph(data.graph);
        message.success('配置已保存，即时生效');
      } else {
        message.error('保存失败');
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading && !memory) return <Spin style={{ display: 'block', marginTop: 40 }} />;
  if (!memory || !graph) return null;

  return (
    <div style={{ height: '64vh', overflowY: 'auto', paddingRight: 8 }}>
      <Title level={5}>记忆配置</Title>
      <Form layout="inline" style={{ marginBottom: 8 }}>
        <Form.Item label="相关记忆条数">
          <InputNumber min={0} max={50} value={memory.memory_relevant_limit}
            onChange={(v) => setMemory({ ...memory, memory_relevant_limit: v })} />
        </Form.Item>
        <Form.Item label="其他记忆条数">
          <InputNumber min={0} max={50} value={memory.memory_other_limit}
            onChange={(v) => setMemory({ ...memory, memory_other_limit: v })} />
        </Form.Item>
        <Form.Item label="注入对方简介">
          <Switch checked={memory.inject_listener_brief}
            onChange={(v) => setMemory({ ...memory, inject_listener_brief: v })} />
        </Form.Item>
        <Form.Item label="相关性过滤">
          <Switch checked={memory.enable_relation_filter}
            onChange={(v) => setMemory({ ...memory, enable_relation_filter: v })} />
        </Form.Item>
      </Form>

      <Divider />
      <Title level={5}>图谱配置</Title>
      <Form layout="inline" style={{ marginBottom: 8 }}>
        <Form.Item label="共同事件条数">
          <InputNumber min={0} max={20} value={graph.common_event_limit}
            onChange={(v) => setGraph({ ...graph, common_event_limit: v })} />
        </Form.Item>
        <Form.Item label="关系网条数">
          <InputNumber min={0} max={30} value={graph.relation_overview_limit}
            onChange={(v) => setGraph({ ...graph, relation_overview_limit: v })} />
        </Form.Item>
        <Form.Item label="图谱文本上限">
          <InputNumber min={0} max={5000} value={graph.graph_text_max_chars}
            onChange={(v) => setGraph({ ...graph, graph_text_max_chars: v })} />
        </Form.Item>
        <Form.Item label="描述截断">
          <InputNumber min={0} max={500} value={graph.desc_max_chars}
            onChange={(v) => setGraph({ ...graph, desc_max_chars: v })} />
        </Form.Item>
        <Form.Item label="显示关系网概览">
          <Switch checked={graph.show_relation_overview}
            onChange={(v) => setGraph({ ...graph, show_relation_overview: v })} />
        </Form.Item>
      </Form>

      <Button type="primary" onClick={save} loading={saving} style={{ marginTop: 16 }}>
        保存（即时生效）
      </Button>
      <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
        记忆/图谱召回都受这些 limit 控制；调小可省 token 防超限，调大召回更多但更费 token。改完即时生效并持久化。
      </Text>
    </div>
  );
}
