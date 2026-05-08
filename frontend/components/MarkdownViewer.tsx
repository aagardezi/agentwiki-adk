'use client';

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// We need a replacement for path.basename that works in browser
const basename = (path: string, ext?: string) => {
    const parts = path.split('/');
    const name = parts[parts.length - 1];
    if (ext && name.endsWith(ext)) {
        return name.slice(0, -ext.length);
    }
    return name;
};

interface MarkdownViewerProps {
  filePath: string;
  onNavigate: (path: string) => void;
}

export default function MarkdownViewer({ filePath, onNavigate }: MarkdownViewerProps) {
  const [content, setContent] = useState('');
  const [metadata, setMetadata] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [allFiles, setAllFiles] = useState<{name: string, tags: string[]}[]>([]);

  useEffect(() => {
    fetch('/api/wiki/list')
      .then(res => res.json())
      .then(data => {
        setAllFiles(data.files || []);
      })
      .catch(err => console.error('Failed to load file list:', err));
  }, []);

  useEffect(() => {
    if (filePath.startsWith('tag:')) {
        setLoading(false);
        setContent('');
        setMetadata({});
        return;
    }

    setLoading(true);
    fetch(`/api/wiki/content?path=${encodeURIComponent(filePath)}`)
      .then(res => res.json())
      .then(data => {
        const rawContent = data.content || 'No content found.';

        
        // Parse frontmatter
        const frontmatterMatch = rawContent.match(/^---([\s\S]*?)---\n?/);
        let cleanedContent = rawContent;
        let metadata: any = {};
        
        if (frontmatterMatch) {
            cleanedContent = rawContent.replace(frontmatterMatch[0], '');
            const fmStr = frontmatterMatch[1];
            
            // Simple YAML-like parser
            const lines = fmStr.split('\n');
            let currentKey = '';
            for (const line of lines) {
                const match = line.match(/^(\w+):\s*(.*)/);
                if (match) {
                    currentKey = match[1];
                    let value = match[2].trim();
                    
                    // Handle lists like [a, b]
                    if (value.startsWith('[') && value.endsWith(']')) {
                        value = value.slice(1, -1).split(',').map(s => s.trim().replace(/['"]/g, ''));
                    }
                    
                    metadata[currentKey] = value;
                } else if (line.startsWith('  - ') && currentKey === 'relationships') {
                    // Handle relationships list
                     if (!metadata.relationships) metadata.relationships = [];
                     // We'll need a more complex parser or just manual extraction for relationships
                }
            }
            
            // Better manual extraction for relationships to avoid complex YAML parser
            const relRegex = /-\s*target:\s*["']([^"']+)["']\s*\n\s*type:\s*["']([^"']+)["']/g;
            let relMatch;
            const relationships = [];
            while ((relMatch = relRegex.exec(fmStr)) !== null) {
                relationships.push({ target: relMatch[1], type: relMatch[2] });
            }
            if (relationships.length > 0) {
                metadata.relationships = relationships;
            }
        }
        
        setMetadata(metadata);
        setContent(cleanedContent);
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
    
    // If relativePath starts with a folder name (e.g., "agents/...", "compliance/..."),
    // it is likely intended to be relative to the bucket root, even if it doesn't have a leading slash.
    // Our sidebar and API use paths relative to the bucket root.
    if (!relativePath.startsWith('.') && relativePath.includes('/')) {
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
      ) : filePath.startsWith('tag:') ? (
        <div className="max-w-3xl mx-auto">
          <div className="mb-4 text-zinc-500 text-sm">{filePath}</div>
          <div className="mb-6 p-4 bg-zinc-900/50 rounded-lg border border-zinc-800">
            <div className="text-xl font-bold text-zinc-100 mb-2">Tag: <span className="text-amber-400">{filePath.substring(4)}</span></div>
            <div className="text-zinc-400 text-sm mb-4">Files associated with this tag:</div>
            
            <ul className="space-y-2">
                {allFiles
                    .filter(file => file.tags && file.tags.includes(filePath.substring(4)))
                    .map(file => (
                        <li key={file.name} className="flex items-center gap-2">
                            <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                            <button
                                onClick={() => onNavigate(file.name)}
                                className="text-blue-400 hover:underline text-sm text-left"
                            >
                                {basename(file.name, '.md')}
                            </button>
                            <span className="text-zinc-600 text-xs">({file.name})</span>
                        </li>
                    ))
                }
            </ul>
            {allFiles.filter(file => file.tags && file.tags.includes(filePath.substring(4))).length === 0 && (
                <div className="text-zinc-600 text-sm">No files found with this tag.</div>
            )}
          </div>
        </div>
      ) : (
        <div className="max-w-3xl mx-auto">
          <div className="mb-4 text-zinc-500 text-sm">{filePath}</div>

          
          {/* Render Metadata */}
          {Object.keys(metadata).length > 0 && (
            <div className="mb-6 p-4 bg-zinc-900/50 rounded-lg border border-zinc-800 text-sm">
                {metadata.title && <div className="text-xl font-bold text-zinc-100 mb-2">{metadata.title}</div>}
                {metadata.description && <div className="text-zinc-400 mb-2">{metadata.description}</div>}
                
                <div className="grid grid-cols-2 gap-2 text-xs text-zinc-500">
                    {metadata.created_at && <div><span className="font-semibold">Created:</span> {metadata.created_at}</div>}
                    {metadata.updated_at && <div><span className="font-semibold">Updated:</span> {metadata.updated_at}</div>}
                    {metadata.date_created && <div><span className="font-semibold">Date Created:</span> {metadata.date_created}</div>}
                    {metadata.source && (
                        <div className="col-span-2">
                            <span className="font-semibold">Source:</span>{' '}
                            {metadata.source.startsWith('http') ? (
                                <a href={metadata.source} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{metadata.source}</a>
                            ) : (
                                <span>{metadata.source}</span>
                            )}
                        </div>
                    )}
                    {metadata.sources && (
                        <div className="col-span-2">
                            <span className="font-semibold">Sources:</span>{' '}
                            {metadata.sources.map((s: string) => (
                                <button 
                                    key={s}
                                    onClick={() => onNavigate(`sources/${s.endsWith('.md') ? s : s + '.md'}`)}
                                    className="text-blue-400 hover:underline mr-2"
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    )}
                    {metadata.tags && (
                        <div className="col-span-2">
                            <span className="font-semibold">Tags:</span>{' '}
                            {metadata.tags.map((t: string) => (
                                <button 
                                    key={t} 
                                    onClick={() => setSelectedTag(selectedTag === t ? null : t)}
                                    className={`px-2 py-0.5 rounded-full mr-1 cursor-pointer ${selectedTag === t ? 'bg-blue-600 text-white' : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'}`}
                                >
                                    {t}
                                </button>
                            ))}
                        </div>
                    )}
                    {metadata.relationships && (
                        <div className="col-span-2 mt-2">
                            <div className="font-semibold mb-1">Relationships:</div>
                            <ul className="list-disc list-inside">
                                {metadata.relationships.map((rel: any, index: number) => (
                                    <li key={index}>
                                        <span className="text-blue-400">{rel.type}</span>{' '}
                                        <button
                                            onClick={() => onNavigate(rel.target)}
                                            className="text-blue-400 hover:underline"
                                        >
                                            {basename(rel.target, '.md')}
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
          )}

          {/* Render Filtered Files by Tag */}
          {selectedTag && (
            <div className="mb-6 p-4 bg-zinc-900/30 rounded-lg border border-blue-900/50 text-sm">
                <div className="flex justify-between items-center mb-2">
                    <div className="font-semibold text-zinc-100">Files tagged with <span className="text-blue-400">{selectedTag}</span>:</div>
                    <button onClick={() => setSelectedTag(null)} className="text-zinc-500 hover:text-zinc-300 text-xs">Clear</button>
                </div>
                <ul className="space-y-1">
                    {allFiles
                        .filter(file => file.tags && file.tags.includes(selectedTag))
                        .map(file => (
                            <li key={file.name}>
                                <button
                                    onClick={() => {
                                        onNavigate(file.name);
                                        setSelectedTag(null);
                                    }}
                                    className="text-blue-400 hover:underline text-xs"
                                >
                                    {file.name}
                                </button>
                            </li>
                        ))
                    }
                </ul>
            </div>
          )}


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
