import { NextResponse } from 'next/server';
import { Storage } from '@google-cloud/storage';

const BUCKET_NAME = process.env.WIKI_BUCKET_NAME || 'agentwiki-adk-wiki-sg';
const storage = new Storage();

export async function GET() {
  try {
    const bucket = storage.bucket(BUCKET_NAME);
    const [files] = await bucket.getFiles();
    
    const fileList = files
      .filter(file => file.name.endsWith('.md'))
      .filter(file => file.name !== 'schema.md'); // Skip schema

    const filesWithTags = await Promise.all(fileList.map(async (file) => {
        try {
            const [contentBuffer] = await file.download();
            const content = contentBuffer.toString('utf-8');
            
            const frontmatterMatch = content.match(/^---[\s\S]*?---/);
            let tags: string[] = [];
            
            if (frontmatterMatch) {
                const frontmatter = frontmatterMatch[0];
                const tagsMatch = frontmatter.match(/tags:\s*\[(.*?)\]/);
                if (tagsMatch) {
                    const tagsStr = tagsMatch[1];
                    tags = tagsStr.split(',').map(s => s.trim().replace(/['"]/g, ''));
                }
            }
            
            return {
                name: file.name,
                tags: tags
            };
        } catch (e) {
            console.error(`Error reading tags for ${file.name}:`, e);
            return { name: file.name, tags: [] };
        }
    }));

    return NextResponse.json({ files: filesWithTags });

  } catch (error) {
    console.error('Error listing wiki files:', error);
    return NextResponse.json({ error: 'Failed to list files' }, { status: 500 });
  }
}
