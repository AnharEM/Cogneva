import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals }) => {
	if (!locals.user) {
		return json({ error: 'Unauthorized' }, { status: 401 });
	}

	const body = await request.json();
	const backendUrl = env.BACKEND_URL || 'http://127.0.0.1:8000';
	
	try {
		const res = await fetch(`${backendUrl}/chat`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-API-Key': env.INTERNAL_API_KEY || 'super-secret-key-123'
			},
			body: JSON.stringify({
				user_id: locals.user.id,
				session_id: body.session_id || locals.user.id,
				user_input: body.user_input
			})
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
