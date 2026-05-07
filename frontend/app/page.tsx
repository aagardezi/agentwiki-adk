'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import MarkdownViewer from '@/components/MarkdownViewer';
import WikiGraph from '@/components/WikiGraph';
import { Network, FileText, Maximize2, Minimize2 } from 'lucide-react';

export default function Home() {
  const [selectedFile, setSelectedFile] = useState('index.md');
  const [showGraph, setShowGraph] = useState(true);
  const [fullscreenGraph, setFullscreenGraph] = useState(false);

  return (
    <div className="flex h-screen bg-black text-zinc-100 overflow-hidden">
      <Sidebar onSelectFile={setSelectedFile} />
      
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="h-12 border-b border-zinc-800 flex items-center justify-between px-4 bg-zinc-900">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-zinc-300">{selectedFile}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowGraph(!showGraph)}
              className={`p-1.5 rounded hover:bg-zinc-800 transition-colors ${showGraph ? 'text-white' : 'text-zinc-500'}`}
              title={showGraph ? 'Hide Graph' : 'Show Graph'}
            >
              <Network size={18} />
            </button>
            {showGraph && (
              <button
                onClick={() => setFullscreenGraph(!fullscreenGraph)}
                className="p-1.5 rounded hover:bg-zinc-800 transition-colors text-zinc-500 hover:text-white"
                title={fullscreenGraph ? 'Restore View' : 'Fullscreen Graph'}
              >
                {fullscreenGraph ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
              </button>
            )}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {(!showGraph || !fullscreenGraph) && (
            <MarkdownViewer filePath={selectedFile} onNavigate={setSelectedFile} />
          )}
          
          {showGraph && (
            <div className={`${fullscreenGraph ? 'w-full' : 'w-1/2'} border-l border-zinc-800`}>
              <WikiGraph onNodeClick={setSelectedFile} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
