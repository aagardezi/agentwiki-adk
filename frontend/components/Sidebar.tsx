'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface WikiFile {
  name: string;
  tags: string[];
}

interface TreeNode {
  name: string;
  path: string;
  children?: TreeNode[];
}

function buildTree(files: {name: string}[]) {
  const root: TreeNode[] = [];
  
  for (const file of files) {
    const parts = file.name.split('/');
    let currentLevel = root;
    
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;
      const path = parts.slice(0, i + 1).join('/');
      
      let node = currentLevel.find(n => n.name === part);
      
      if (!node) {
        node = { name: part, path };
        if (!isFile) {
          node.children = [];
        }
        currentLevel.push(node);
      }
      
      if (node.children) {
        currentLevel = node.children;
      }
    }
  }
  
  // Sort so folders are first, then files
  root.sort((a, b) => {
    if (a.children && !b.children) return -1;
    if (!a.children && b.children) return 1;
    return a.name.localeCompare(b.name);
  });

  // Recursively sort children
  const sortChildren = (nodes: TreeNode[]) => {
      nodes.forEach(n => {
          if (n.children) {
              n.children.sort((a, b) => {
                  if (a.children && !b.children) return -1;
                  if (!a.children && b.children) return 1;
                  return a.name.localeCompare(b.name);
              });
              sortChildren(n.children);
          }
      });
  };
  sortChildren(root);

  return root;
}

function TreeItem({ node, onSelectFile, depth = 0 }: { node: TreeNode, onSelectFile: (path: string) => void, depth?: number }) {
  const [expanded, setExpanded] = useState(false);
  const isFile = !node.children;

  
  return (
    <div style={{ paddingLeft: `${depth * 8}px` }}>
      {isFile ? (
        <button
          onClick={() => onSelectFile(node.path)}
          className="text-sm text-zinc-300 hover:text-white hover:bg-zinc-800 w-full text-left px-2 py-1 rounded transition-colors flex items-center gap-2"
        >
          <span className="text-zinc-600">📄</span>
          <span>{node.name.endsWith('.md') ? node.name.slice(0, -3) : node.name}</span>
        </button>
      ) : (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-zinc-400 hover:text-white w-full text-left px-2 py-1 flex items-center justify-between font-semibold"
          >
            <span className="flex items-center gap-2">
                <span className="text-amber-500">{expanded ? '📂' : '📁'}</span>
                <span>{node.name}</span>
            </span>
            <span className="text-xs text-zinc-600">{expanded ? '▲' : '▼'}</span>
          </button>
          {expanded && (
            <div className="border-l border-zinc-800 ml-1">
              {node.children?.map(child => (
                <TreeItem key={child.path} node={child} onSelectFile={onSelectFile} depth={depth + 1} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>

  );
}

export default function Sidebar({ onSelectFile }: { onSelectFile: (path: string) => void }) {
  const [files, setFiles] = useState<{name: string, tags: string[]}[]>([]);
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

  const tree = buildTree(files);

  return (
    <div className="w-64 bg-zinc-900 text-zinc-100 h-full flex flex-col border-r border-zinc-800">
      <div className="p-4 border-b border-zinc-800">
        <h1 className="text-lg font-semibold text-white">Knowledge Agent Wiki</h1>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {loading ? (
          <div className="text-zinc-500 p-2">Loading...</div>
        ) : (
          <nav className="space-y-1">
            {tree.map(node => (
              <TreeItem key={node.path} node={node} onSelectFile={onSelectFile} />
            ))}
          </nav>
        )}
      </div>
    </div>
  );
}

