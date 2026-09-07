import { multiplayerDb } from '@/lib/multiplayer-db';
import { multiplayerRequest } from '@/lib/multiplayer-server';
export const dynamic = 'force-dynamic';
export async function POST(request: Request) {
  return multiplayerRequest(request, multiplayerDb());
}
