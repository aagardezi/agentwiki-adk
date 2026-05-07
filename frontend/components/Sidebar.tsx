'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface WikiFile {
  name: string;
  title: string;
}

export default function Sidebar({ onSelectFile }: { onSelectFile: (path: string) => void }) {
  const [files, setFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/wiki/list')
      .then(res => res.json())
      .then(data => {
        setFiles(data.files || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load files:', err);
        setLoading(false);
      });
  }, []);

  const groupedFiles = files.reduce((acc, file) => {
    const parts = file.split('/');
    if (parts.length > 1) {
      const dir = parts[0];
      if (!acc[dir]) acc[dir] = [];
      acc[dir].push(file);
    } else {
      if (!acc['root']) acc['root'] = [];
      acc['root'].push(file);
    }
    return acc;
  }, {} as Record<string, string[]>);

  return (
    <div className="w-64 bg-zinc-900 text-zinc-100 h-full flex flex-col border-r border-zinc-800">
      <div className="p-4 border-b border-zinc-800">
        <h1 className="text-lg font-semibold text-white">LLM Wiki</h1>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {loading ? (
          <div className="text-zinc-500 p-2">Loading...</div>
        ) : (
          <nav className="space-y-4">
            {Object.entries(groupedFiles).map(([dir, files]) => (
              <div key={dir}>
                <h2 className="text-xs uppercase text-zinc-500 font-bold mb-1 px-2">{dir}</h2>
                <ul className="space-y-0.5">
                  {files.map(file => (
                    <li key={file}>
                      <button
                        onClick={() => onSelectFile(file)}
                        className="text-sm text-zinc-300 hover:text-white hover:bg-zinc-800 w-full text-left px-2 py-1 rounded transition-colors"
                      >
                        {file.split('/').pop()?.replace('.md', '')}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        )}
      </div>
    </div>
  );
}
