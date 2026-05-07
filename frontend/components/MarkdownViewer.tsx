'use client';

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownViewerProps {
  filePath: string;
  onNavigate: (path: string) => void;
}

export default function MarkdownViewer({ filePath, onNavigate }: MarkdownViewerProps) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/wiki/content?path=${encodeURIComponent(filePath)}`)
      .then(res => res.json())
      .then(data => {
        setContent(data.content || 'No content found.');
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load content:', err);
        setContent('Error loading content.');
        setLoading(false);
      });
  }, [filePath]);

  // Helper to resolve relative paths
  const resolvePath = (currentPath: string, relativePath: string) => {
    if (relativePath.startsWith('http') || relativePath.startsWith('#')) {
        return relativePath;
    }
    
    const pathParts = currentPath.split('/').filter(Boolean);
    pathParts.pop(); // Remove file name
    const currentDir = pathParts.join('/');
    let resolved = relativePath;
    
    if (relativePath.startsWith('../')) {
        const parts = currentDir.split('/').filter(Boolean);
        const relParts = relativePath.split('/');
        
        for (const part of relParts) {
            if (part === '..') {
                parts.pop();
            } else if (part !== '.') {
                parts.push(part);
            }
        }
        resolved = parts.join('/');
    } else if (!relativePath.startsWith('/')) {
        // Same directory
        if (currentDir !== '.') {
            resolved = `${currentDir}/${relativePath}`;
        }
    }
    
    return resolved;
  };

  return (
    <div className="flex-1 overflow-y-auto bg-black text-zinc-100 p-8">
      {loading ? (
        <div className="text-zinc-500">Loading {filePath}...</div>
      ) : (
        <div className="max-w-3xl mx-auto">
          <div className="mb-4 text-zinc-500 text-sm">{filePath}</div>
          <div className="prose prose-invert max-w-none">
             <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                    a: ({ node, ...props }) => {
                        const href = props.href || '';
                        const isExternal = href.startsWith('http');
                        
                        if (isExternal) {
                            return <a {...props} target="_blank" rel="noopener noreferrer" />;
                        }
                        
                        return (
                            <button
                                onClick={() => {
                                    const resolved = resolvePath(filePath, href);
                                    console.log(`Navigating to: ${resolved} (from ${filePath} + ${href})`);
                                    onNavigate(resolved);
                                }}
                                className="text-blue-400 hover:underline cursor-pointer text-left"
                            >
                                {props.children}
                            </button>
                        );
                    }
                }}
             >
                 {content}
             </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
