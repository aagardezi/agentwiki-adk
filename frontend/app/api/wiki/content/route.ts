import { NextResponse } from 'next/server';
import { Storage } from '@google-cloud/storage';
import path from 'path';

const BUCKET_NAME = process.env.WIKI_BUCKET_NAME || 'YOUR_WIKI_BUCKET_NAME';
const storage = new Storage();

function getContentType(filePath: string, gcsContentType?: string): string {
  if (gcsContentType) return gcsContentType;
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case '.md': return 'text/markdown';
    case '.txt': return 'text/plain';
    case '.pdf': return 'application/pdf';
    case '.png': return 'image/png';
    case '.jpg':
    case '.jpeg': return 'image/jpeg';
    case '.gif': return 'image/gif';
    case '.svg': return 'image/svg+xml';
    case '.webp': return 'image/webp';
    default: return 'application/octet-stream';
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const filePath = searchParams.get('path') || 'index.md';

  try {
    const bucket = storage.bucket(BUCKET_NAME);
    const file = bucket.file(filePath);

    const [exists] = await file.exists();
    if (!exists) {
      return NextResponse.json({ error: 'File not found' }, { status: 404 });
    }

    const [metadata] = await file.getMetadata();
    const contentType = getContentType(filePath, metadata.contentType);
    const isBinary = !contentType.startsWith('text/') && contentType !== 'application/json';

    const [content] = await file.download();
    
    if (isBinary) {
      return NextResponse.json({
        isBinary: true,
        contentType: contentType,
        content: content.toString('base64')
      });
    }

    return NextResponse.json({
      isBinary: false,
      contentType: contentType,
      content: content.toString('utf-8')
    });
  } catch (error) {
    console.error('Error fetching wiki file:', error);
    return NextResponse.json({ error: 'Failed to fetch file' }, { status: 500 });
  }
}
