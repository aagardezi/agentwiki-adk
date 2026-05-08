'use client';

import { useEffect, useState, useRef } from 'react';
import dynamic from 'next/dynamic';

// ForceGraph2D needs to be imported dynamically as it relies on browser APIs
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

interface GraphData {
  nodes: any[];
  links: any[];
}

export default function WikiGraph({ onNodeClick, focusedNodeId }: { onNodeClick: (nodeId: string) => void, focusedNodeId?: string }) {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [filteredData, setFilteredData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [isFiltered, setIsFiltered] = useState(false);
  const [hasCentered, setHasCentered] = useState(false);
  const fgRef = useRef<any>();


  useEffect(() => {
    fetch('/api/wiki/graph')
      .then(res => res.json())
      .then(data => {
        if (data.nodes && data.links) {
            setGraphData(data);
            setFilteredData(data);
            
            // Zoom to fit after data is loaded and state is updated
            setTimeout(() => {
                if (fgRef.current) {
                    fgRef.current.zoomToFit(400, 50);
                }
            }, 500);
        } else {
            console.error('Invalid graph data received:', data);
        }
        setLoading(false);
      })

      .catch(err => {
        console.error('Failed to load graph data:', err);
        setLoading(false);
      });
  }, []);


  useEffect(() => {
    if (focusedNodeId && focusedNodeId !== 'index.md' && graphData.nodes?.length > 0) {
        // Find neighbors
        const neighbors = new Set<string>();
        neighbors.add(focusedNodeId);

        
        graphData.links.forEach(link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            
            if (sourceId === focusedNodeId) {
                neighbors.add(targetId);
            } else if (targetId === focusedNodeId) {
                neighbors.add(sourceId);
            }
        });
        
        const filteredNodes = graphData.nodes.filter(node => neighbors.has(node.id));
        const filteredLinks = graphData.links.filter(link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            return neighbors.has(sourceId) && neighbors.has(targetId);
        });
        
        setFilteredData({ nodes: filteredNodes, links: filteredLinks });
        setIsFiltered(true);
        
        // Center on node
        const node = graphData.nodes.find(n => n.id === focusedNodeId);
        if (node && fgRef.current) {
            fgRef.current.centerAt(node.x, node.y, 1000);
            fgRef.current.zoom(2, 1000);
        }
    } else if (focusedNodeId === 'index.md' && graphData.nodes?.length > 0) {
        // Reset to full graph when index is selected
        setFilteredData(graphData);
        setIsFiltered(false);
        if (fgRef.current && hasCentered) {
            fgRef.current.centerAt(0, 0, 1000);
            fgRef.current.zoom(1, 1000);
        }
    }

  }, [focusedNodeId, graphData, hasCentered]);



  const handleReset = () => {
      setFilteredData(graphData);
      setIsFiltered(false);
      if (fgRef.current) {
          fgRef.current.centerAt(0, 0, 1000);
          fgRef.current.zoom(1, 1000);
      }
  };


  const getColor = (group: string) => {
    switch (group) {
      case 'entity': return '#60a5fa'; // blue
      case 'concept': return '#34d399'; // green
      case 'source': return '#f87171'; // red
      case 'index': return '#e879f9'; // pink
      case 'tag': return '#fbbf24'; // amber
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
          graphData={filteredData}
          nodeLabel="label"

          nodeColor={node => getColor((node as any).group)}
          nodeRelSize={6}
          linkDirectionalParticles={link => (link as any).isExplicit ? 4 : 2}
          linkDirectionalParticleSpeed={0.005}
          linkColor={link => (link as any).isExplicit ? '#60a5fa' : '#3f3f46'}
          linkWidth={link => (link as any).isExplicit ? 2 : 1}
          linkLabel={link => (link as any).isExplicit ? `<span class="text-blue-400">${(link as any).label}</span>` : ''}
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
      {isFiltered && (
        <button
            onClick={handleReset}
            className="absolute top-4 right-4 bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded shadow-lg transition-colors"
        >
            Reset View
        </button>
      )}
      <div className="absolute bottom-4 left-4 bg-zinc-900/80 p-2 rounded text-xs text-zinc-400 backdrop-blur-sm border border-zinc-800">

         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-pink-400 rounded-full"></span> Index</div>
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-blue-400 rounded-full"></span> Entity</div>
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-green-400 rounded-full"></span> Concept</div>
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-red-400 rounded-full"></span> Source</div>
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-yellow-500 rounded-full"></span> Tag</div>
         <div className="flex items-center gap-2"><span className="w-3 h-3 bg-gray-400 rounded-full"></span> Other</div>
      </div>
    </div>
  );
}
