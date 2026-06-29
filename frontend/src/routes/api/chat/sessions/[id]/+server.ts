import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

export const PUT: RequestHandler = async ({ params, request, locals }) => {
	if (!locals.user) return json({ error: 'Unauthorized' }, { status: 401 });
	const backendUrl = env.BACKEND_URL || 'http://127.0.0.1:8000';
	
	try {
		const body = await request.json();
		const res = await fetch(`${backendUrl}/chat/sessions/${params.id}`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				'X-API-Key': env.INTERNAL_API_KEY || 'super-secret-key-123'
			},
			body: JSON.stringify(body)
		});
		if (!res.ok) return json({ error: 'Backend error' }, { status: res.status });
		return json(await res.json());
	} catch (e) {
		return json({ error: 'Backend unreachable' }, { status: 502 });
	}
};

export const DELETE: RequestHandler = async ({ params, locals }) => {
	if (!locals.user) return json({ error: 'Unauthorized' }, { status: 401 });
	const backendUrl = env.BACKEND_URL || 'http://127.0.0.1:8000';
	
	try {
		const res = await fetch(`${backendUrl}/chat/sessions/${params.id}`, {
			method: 'DELETE',
			headers: { 'X-API-Key': env.INTERNAL_API_KEY || 'super-secret-key-123' }
		});
		if (!res.ok) return json({ error: 'Backend error' }, { status: res.status });
		return json(await res.json());
	} catch (e) {
		return json({ error: 'Backend unreachable' }, { status: 502 });
	}
};
