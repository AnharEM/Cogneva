import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ locals }) => {
	if (!locals.user) return json({ error: 'Unauthorized' }, { status: 401 });
	const backendUrl = env.BACKEND_URL || 'http://127.0.0.1:8000';
	
	try {
		const res = await fetch(`${backendUrl}/chat/sessions/${locals.user.id}`, {
			headers: { 'X-API-Key': env.INTERNAL_API_KEY || 'super-secret-key-123' }
		});
		if (!res.ok) return json({ error: 'Backend error' }, { status: res.status });
		return json(await res.json());
	} catch (e) {
		return json({ error: 'Backend unreachable' }, { status: 502 });
	}
};
