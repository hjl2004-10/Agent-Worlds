/**
 * GraphView - 知识图谱关系网可视化 (力导向图)
 *
 * 拉 /api/graph/subgraph, 用 react-force-graph-2d 渲染节点+边。
 * 关键: react-force-graph 的 canvas 默认用 window 尺寸会溢出父容器,
 *       必须用 ResizeObserver 测量父容器尺寸, 显式传 width/height 约束。
 * 布局与 DebugPanel 对话调试 tab 对齐 (64vh 容器)。
 */
import { useState, useEffect, useCallback, useRef } from 'react';
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore - react-force-graph-2d 自带类型较弱
import ForceGraph2D from 'react-force-graph-2d';
import { Input, Button, Space, Typography, Empty } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { graphApi } from '@/api/god';

const { Text } = Typography;

const KIND_COLOR: Record<string, string> = {
  person: '#40a9ff',
  item: '#faad14',
  place: '#52c41a',
  topic: '#b37feb',
  concept: '#eb2f96',
  event: '#fa8c16',
};

export function GraphView() {
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [npc, setNpc] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 400 });

  // 测量父容器尺寸, 约束 ForceGraph2D 的 canvas (否则用 window 尺寸溢出)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () =>
      setSize({ width: Math.floor(el.clientWidth), height: Math.floor(el.clientHeight) });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const fetchGraph = async () => {
    setLoading(true);
    try {
      const { data: d } = await graphApi.getSubgraph(npc.trim() || undefined);
      if (d.status === 'ok') {
        setGraphData({
          nodes: d.nodes.map((n: any) => ({ id: n.id, name: n.name, kind: n.kind })),
          links: d.edges.map((e: any) => ({ source: e.source, target: e.target, label: e.label })),
        });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [npc]);

  const drawNode = useCallback((node: any, ctx: any, scale: number) => {
    const r = 7;
    ctx.fillStyle = KIND_COLOR[node.kind] || '#888';
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = '#eee';
    ctx.font = `${Math.max(8, 11 / scale)}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText(node.name, node.x, node.y + r + 11 / scale);
  }, []);

  return (
    <div style={{ height: '64vh', display: 'flex', flexDirection: 'column' }}>
      <Space style={{ marginBottom: 8 }} wrap>
        <Input.Search
          placeholder="按 NPC 过滤邻域 (空=全图)"
          value={npc}
          onChange={(e) => setNpc(e.target.value)}
          style={{ width: 220 }}
          allowClear
        />
        <Button size="small" icon={<ReloadOutlined />} onClick={fetchGraph} loading={loading}>
          刷新
        </Button>
        <Text type="secondary">
          {graphData.nodes.length} 节点 / {graphData.links.length} 关系
        </Text>
        <span style={{ color: '#888', fontSize: 11, marginLeft: 8 }}>
          {Object.entries(KIND_COLOR).map(([k, c]) => (
            <span key={k} style={{ marginRight: 8 }}>
              <span style={{ display: 'inline-block', width: 8, height: 8, background: c, marginRight: 3, verticalAlign: 'middle' }} />
              {k}
            </span>
          ))}
        </span>
      </Space>

      <div
        ref={containerRef}
        style={{ flex: 1, minHeight: 0, background: '#0a0a0a', border: '1px solid #333', position: 'relative', overflow: 'hidden' }}
      >
        {graphData.nodes.length === 0 ? (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Empty description="图谱为空 (还没有节点或关系)" />
          </div>
        ) : (
          <ForceGraph2D
            graphData={graphData}
            width={size.width}
            height={size.height}
            nodeRelSize={7}
            nodeCanvasObject={drawNode}
            nodeCanvasObjectMode={() => 'after' as const}
            linkLabel={(l: any) => l.label || ''}
            linkColor={() => '#666'}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            backgroundColor="#0a0a0a"
          />
        )}
      </div>
    </div>
  );
}
