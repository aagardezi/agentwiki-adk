import { NextResponse } from 'next/server';
import { Storage } from '@google-cloud/storage';
import path from 'path';

const BUCKET_NAME = process.env.WIKI_BUCKET_NAME || 'agentwiki-adk-wiki-sg';
const storage = new Storage();

interface Node {
  id: string;
  label: string;
  group: string;
}

interface Link {
  source: string;
  target: string;
}

export async function GET() {
  try {
    const bucket = storage.bucket(BUCKET_NAME);
    const [files] = await bucket.getFiles();
    
    const markdownFiles = files.filter(file => file.name.endsWith('.md'));
    
    const nodes: Node[] = [];
    const links: Link[] = [];
    
    // Map to keep track of added nodes to avoid duplicates
    const nodeIds = new Set<string>();

    for (const file of markdownFiles) {
      const id = file.name;
      
      // Skip schema.md as it contains examples that pollute the graph
      if (id === 'schema.md') {
          console.log('Skipping schema.md');
          continue;
      }

      const label = path.basename(id, '.md');
      let group = 'other';
      
      if (id.startsWith('entities/')) group = 'entity';
      else if (id.startsWith('concepts/')) group = 'concept';
      else if (id.startsWith('sources/')) group = 'source';
      else if (id === 'index.md') group = 'index';

      if (!nodeIds.has(id)) {
        nodes.push({ id, label, group });
        nodeIds.add(id);
      }

      try {
        const [contentBuffer] = await file.download();
        const content = contentBuffer.toString('utf-8');
        
        console.log(`Parsing ${id}...`);

        // Parse frontmatter sources
        const frontmatterMatch = content.match(/^---[\s\S]*?---/);
        if (frontmatterMatch) {
            const frontmatter = frontmatterMatch[0];
            const sourcesMatch = frontmatter.match(/sources:\s*\[(.*?)\]/);
            if (sourcesMatch) {
                const sourcesStr = sourcesMatch[1];
                const sources = sourcesStr.split(',').map(s => s.trim().replace(/['"]/g, ''));
                for (const source of sources) {
                    if (source) {
                        let sourcePath = source;
                        if (!sourcePath.startsWith('sources/')) {
                            sourcePath = `sources/${sourcePath}`;
                        }
                        if (!sourcePath.endsWith('.md')) {
                            sourcePath += '.md';
                        }
                        console.log(`  Found frontmatter source link: ${id} -> ${sourcePath}`);
                        links.push({ source: id, target: sourcePath });
                        
                        if (!nodeIds.has(sourcePath)) {
                            nodes.push({ id: sourcePath, label: path.basename(sourcePath, '.md'), group: 'source' });
                            nodeIds.add(sourcePath);
                        }
                    }
                }
            }
        }
        
        // Improved regex to find markdown links: [Text](path.md) or [[wikilink]]
        const linkRegex = /\[\[([^\]]+)\]\]|\[([^\]]+)\]\(([^)]+)\)/g;
        let match;
        
        while ((match = linkRegex.exec(content)) !== null) {
          let targetId = match[3] || match[1]; // match[3] for [text](path), match[1] for [[wikilink]]
          
          if (targetId && !targetId.startsWith('http') && !targetId.startsWith('#')) {
             // Normalize path
             if (!targetId.endsWith('.md') && !targetId.includes('.')) {
                 targetId += '.md';
             }
             
             let resolvedTarget = targetId;
             
             // Handle relative paths
             if (targetId.startsWith('../')) {
                 const idParts = id.split('/');
                 const targetParts = targetId.split('/');
                 
                 // Pop the current file name
                 idParts.pop(); 
                 
                 for (const part of targetParts) {
                     if (part === '..') {
                         idParts.pop();
                     } else if (part !== '.') {
                         idParts.push(part);
                     }
                 }
                 resolvedTarget = idParts.join('/');
             } else if (!targetId.startsWith('entities/') && !targetId.startsWith('concepts/') && !targetId.startsWith('sources/')) {
                 // Assume same directory as source file
                 const dir = path.dirname(id);
                 if (dir !== '.') {
                     resolvedTarget = path.join(dir, targetId);
                 }
             }
             
             // Ensure we don't link to ourselves
             if (resolvedTarget !== id) {
                 console.log(`  Found link: ${id} -> ${resolvedTarget}`);
                 links.push({ source: id, target: resolvedTarget });
                 
                 // Add target node if not exists (might not be in file list if broken link)
                 if (!nodeIds.has(resolvedTarget)) {
                      let group = 'unknown';
                      if (resolvedTarget.startsWith('entities/')) group = 'entity';
                      else if (resolvedTarget.startsWith('concepts/')) group = 'concept';
                      else if (resolvedTarget.startsWith('sources/')) group = 'source';
                      
                      nodes.push({ id: resolvedTarget, label: path.basename(resolvedTarget, '.md'), group });
                      nodeIds.add(resolvedTarget);
                 }
             }
          }
        }
      } catch (e) {
          console.error(`Error parsing links for ${id}:`, e);
      }
    }

    return NextResponse.json({ nodes, links });
  } catch (error) {
    console.error('Error generating graph data:', error);
    return NextResponse.json({ error: 'Failed to generate graph data' }, { status: 500 });
  }
}
