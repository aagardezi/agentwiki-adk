import { NextResponse } from 'next/server';
import { Storage } from '@google-cloud/storage';
import path from 'path';

const BUCKET_NAME = process.env.WIKI_BUCKET_NAME || 'YOUR_WIKI_BUCKET_NAME';
const storage = new Storage();

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

    const [content] = await file.download();
    return NextResponse.json({ content: content.toString('utf-8') });
  } catch (error) {
    console.error('Error fetching wiki file:', error);
    return NextResponse.json({ error: 'Failed to fetch file' }, { status: 500 });
  }
}
