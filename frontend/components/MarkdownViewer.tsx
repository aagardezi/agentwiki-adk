'use client';

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// We need a replacement for path.basename that works in browser
const basename = (path: string, ext?: string) => {
    if (!path) return '';
    const parts = path.split('/');
    const name = parts[parts.length - 1];
    if (ext && name.endsWith(ext)) {
        return name.slice(0, -ext.length);
    }
    return name;
};

const normalizePath = (path: string) => {
    if (!path) return '';
    const parts = path.split('/');
    const stack: string[] = [];
    for (const part of parts) {
        if (part === '.' || part === '') {
            continue;
        }
        if (part === '..') {
            stack.pop();
        } else {
            stack.push(part);
        }
    }
    return (path.startsWith('/') ? '/' : '') + stack.join('/');
};

interface MarkdownViewerProps {
  filePath: string;
  onNavigate: (path: string) => void;
}

export default function MarkdownViewer({ filePath, onNavigate }: MarkdownViewerProps) {
  const [isBinary, setIsBinary] = useState(false);
  const [contentType, setContentType] = useState('');
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
        setIsBinary(false);
        setContentType('');
        return;
    }

    setLoading(true);
    fetch(`/api/wiki/content?path=${encodeURIComponent(filePath)}`)
      .then(res => res.json())
      .then(data => {
        if (data.isBinary) {
          setIsBinary(true);
          setContentType(data.contentType);
          setContent(data.content);
          setMetadata({});
          setLoading(false);
          return;
        }

        setIsBinary(false);
        setContentType(data.contentType || 'text/markdown');
        const rawContent = data.content || 'No content found.';

        
        // Parse frontmatter
        const frontmatterMatch = rawContent.match(/^---([\s\S]*?)---\n?/);
        let cleanedContent = rawContent;
        let metadata: any = {};
        
        if (frontmatterMatch) {
            cleanedContent = rawContent.replace(frontmatterMatch[0], '');
            const fmStr = frontmatterMatch[1];
            
            // Robust YAML-like line-by-line block parser
            const lines = fmStr.split('\n');
            let currentKey = '';
            let currentList: any[] = [];
            let currentItem: any = null;

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;

                if (line.startsWith('  - ')) {
                    if (currentItem) currentList.push(currentItem);
                    currentItem = {};
                    const lineContent = line.substring(4).trim();
                    const match = lineContent.match(/^(\w+):\s*(.*)/);
                    if (match) {
                        const k = match[1];
                        let v = match[2].trim();
                        if (v.startsWith('"') || v.startsWith("'")) v = v.slice(1, -1);
                        currentItem[k] = v;
                    }
                } else if (line.startsWith('    ') && currentItem) {
                    const match = trimmed.match(/^(\w+):\s*(.*)/);
                    if (match) {
                        const k = match[1];
                        let v = match[2].trim();
                        if (v.startsWith('"') || v.startsWith("'")) v = v.slice(1, -1);
                        currentItem[k] = v;
                    }
                } else {
                    if (currentItem) {
                        currentList.push(currentItem);
                        currentItem = null;
                    }
                    if (currentKey && currentList.length > 0) {
                        metadata[currentKey] = currentList;
                        currentList = [];
                    }

                    const match = trimmed.match(/^(\w+):\s*(.*)/);
                    if (match) {
                        currentKey = match[1];
                        let value = match[2].trim();

                        if (value.startsWith('[') && value.endsWith(']')) {
                            metadata[currentKey] = value.slice(1, -1).split(',').map((s: string) => s.trim().replace(/['"]/g, '')).filter(Boolean);
                        } else if (value === 'true') {
                            metadata[currentKey] = true;
                        } else if (value === 'false') {
                            metadata[currentKey] = false;
                        } else if (!isNaN(Number(value)) && value !== '') {
                            metadata[currentKey] = Number(value);
                        } else {
                            if (value.startsWith('"') || value.startsWith("'")) value = value.slice(1, -1);
                            metadata[currentKey] = value;
                        }
                    }
                }
            }

            if (currentItem) currentList.push(currentItem);
            if (currentKey && currentList.length > 0) {
                metadata[currentKey] = currentList;
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
    
    let resolved = relativePath;
    
    // If relativePath starts with a folder name (e.g., "agents/...", "compliance/..."),
    // it is likely intended to be relative to the bucket root, even if it doesn't have a leading slash.
    // Our sidebar and API use paths relative to the bucket root.
    if (!relativePath.startsWith('.') && relativePath.includes('/')) {
        resolved = relativePath;
    } else {
        const pathParts = currentPath.split('/').filter(Boolean);
        pathParts.pop(); // Remove file name
        const currentDir = pathParts.join('/');
        
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
            if (currentDir && currentDir !== '.') {
                resolved = `${currentDir}/${relativePath}`;
            } else {
                resolved = relativePath;
            }
        }
    }
    
    return normalizePath(resolved);
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
                    .filter(file => file.tags && file.tags.map(t => t.toLowerCase()).includes(filePath.substring(4).toLowerCase()))
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
            {allFiles.filter(file => file.tags && file.tags.map(t => t.toLowerCase()).includes(filePath.substring(4).toLowerCase())).length === 0 && (
                <div className="text-zinc-600 text-sm">No files found with this tag.</div>
            )}
          </div>
        </div>
      ) : isBinary ? (
        <div className="max-w-3xl mx-auto">
          <div className="mb-4 text-zinc-500 text-sm">{filePath}</div>
          
          <div className="mb-6">
            {contentType === 'application/pdf' ? (
              <iframe
                src={`data:${contentType};base64,${content}`}
                className="w-full h-[600px] border border-zinc-800 rounded-lg bg-zinc-900"
                title={filePath}
              />
            ) : contentType.startsWith('image/') ? (
              <img
                src={`data:${contentType};base64,${content}`}
                alt={filePath}
                className="max-w-full h-auto mx-auto rounded-lg border border-zinc-800"
              />
            ) : (
              <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg text-sm text-zinc-400">
                Preview not supported for this file type ({contentType}).
              </div>
            )}
          </div>
          
          <div className="flex justify-end mt-4">
            <a
              href={`data:${contentType};base64,${content}`}
              download={basename(filePath)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-lg transition-colors"
            >
              Download File
            </a>
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
                
                {/* Styled Badges for Status and Confidence */}
                <div className="flex flex-wrap items-center gap-2 mb-4">
                    {metadata.status && (
                        <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${
                            metadata.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            metadata.status === 'stub' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                            'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        }`}>
                            Status: {metadata.status.toUpperCase()}
                        </span>
                    )}
                    {metadata.confidence !== undefined && (
                        <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1.5">
                            Confidence: {Math.round(metadata.confidence * 100)}%
                            <span className="inline-block w-2 h-2 rounded-full bg-blue-400" style={{ opacity: metadata.confidence }}></span>
                        </span>
                    )}
                    {metadata.evidence_count !== undefined && (
                        <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
                            Evidence Count: {metadata.evidence_count}
                        </span>
                    )}
                </div>

                {/* Contested Alert Banner */}
                {metadata.contested === true && (
                    <div className="mb-4 p-3 bg-rose-950/40 border border-rose-800 text-rose-200 text-xs rounded-lg flex items-center gap-2">
                        <span className="text-base">⚠️</span>
                        <div>
                            <strong className="text-rose-400">CONTESTED KNOWLEDGE:</strong> This page contains conflicting or contradictory claims. Please verify sources below.
                        </div>
                    </div>
                )}

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
                                    <li key={index} className="text-zinc-400">
                                        <span className="text-blue-400">{rel.type}</span>{' '}
                                        <button
                                            onClick={() => onNavigate(rel.target)}
                                            className="text-blue-400 hover:underline mr-1.5 font-medium"
                                        >
                                            {basename(rel.target, '.md')}
                                        </button>
                                        {rel.description && (
                                            <span className="text-zinc-500 italic text-xs">({rel.description})</span>
                                        )}
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
                        .filter(file => file.tags && file.tags.map(t => t.toLowerCase()).includes(selectedTag.toLowerCase()))
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
