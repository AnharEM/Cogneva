import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url, locals }) => {
	if (!locals.user) {
		return json({ error: 'Unauthorized' }, { status: 401 });
	}

	const sessionId = url.searchParams.get('session_id') || locals.user.id;
	const backendUrl = env.BACKEND_URL || 'http://127.0.0.1:8000';
	
	try {
		const res = await fetch(`${backendUrl}/chat/history/${sessionId}`, {
			method: 'GET',
			headers: {
				'X-API-Key': env.INTERNAL_API_KEY || 'super-secret-key-123'
			}
		});
		
		if (!res.ok) {
			return json({ error: 'Backend error' }, { status: res.status });
		}
		
		const data = await res.json();
		return json(data);
	} catch (e) {
		console.error("Backend connection failed:", e);
		return json({ error: 'Backend unreachable' }, { status: 502 });
	}
};
