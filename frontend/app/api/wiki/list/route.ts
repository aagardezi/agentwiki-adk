import { NextResponse } from 'next/server';
import { Storage } from '@google-cloud/storage';

const BUCKET_NAME = process.env.WIKI_BUCKET_NAME || 'agentwiki-adk-wiki-sg';
const storage = new Storage();

export async function GET() {
  try {
    const bucket = storage.bucket(BUCKET_NAME);
    const [files] = await bucket.getFiles();
    
    const fileList = files
      .map(file => file.name)
      .filter(name => name.endsWith('.md'));

    return NextResponse.json({ files: fileList });
  } catch (error) {
    console.error('Error listing wiki files:', error);
    return NextResponse.json({ error: 'Failed to list files' }, { status: 500 });
  }
}
