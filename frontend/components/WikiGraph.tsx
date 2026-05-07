'use client';

import { useEffect, useState, useRef } from 'react';
import dynamic from 'next/dynamic';

// ForceGraph2D needs to be imported dynamically as it relies on browser APIs
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

interface GraphData {
  nodes: any[];
  links: any[];
}

export default function WikiGraph({ onNodeClick }: { onNodeClick: (nodeId: string) => void }) {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const fgRef = useRef<any>();

  useEffect(() => {
    fetch('/api/wiki/graph')
      .then(res => res.json())
      .then(data => {
        setGraphData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load graph data:', err);
        setLoading(false);
      });
  }, []);

  const getColor = (group: string) => {
    switch (group) {
      case 'entity': return '#60a5fa'; // blue
      case 'concept': return '#34d399'; // green
      case 'source': return '#f87171'; // red
      case 'index': return '#e879f9'; // pink
      default: return '#9ca3af'; // gray
    }
  };

  return (
    <div className="h-full bg-zinc-950 relative">
      {loading ? (
        <div className="text-zinc-500 absolute inset-0 flex items-center justify-center">Loading Graph...</div>
      ) : (
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          nodeLabel="label"
          nodeColor={node => getColor((node as any).group)}
          nodeRelSize={6}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.005}
          linkColor={() => '#3f3f46'}
          onNodeClick={(node) => onNodeClick((node as any).id)}
          cooldownTicks={100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const label = (node as any).label;
            const fontSize = 12 / globalScale;
            ctx.font = `${fontSize}px Sans-Serif`;
            const textWidth = ctx.measureText(label).width;
            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); // some padding

            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.beginPath();
            ctx.arc((node as any).x, (node as any).y, 6, 0, 2 * Math.PI, false);
            ctx.fillStyle = getColor((node as any).group);
            ctx.fill();

            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#a1a1aa'; // zinc-400
            ctx.fillText(label, (node as any).x, (node as any).y + 12);
          }}
        />
      )}
      <div className="absolute bottom-4 left-4 bg-zinc-900/80 p-2 rounded text-xs text-zinc-400 backdrop-blur-sm border border-zinc-800">
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-pink-400 rounded-full"></span> Index</div>
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-blue-400 rounded-full"></span> Entity</div>
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-green-400 rounded-full"></span> Concept</div>
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-red-400 rounded-full"></span> Source</div>
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-gray-400 rounded-full"></span> Other</div>
      </div>
    </div>
  );
}
