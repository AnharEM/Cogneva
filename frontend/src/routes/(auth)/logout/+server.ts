import { redirect } from '@sveltejs/kit';
import { invalidateSession } from '$lib/server/auth';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ cookies }) => {
	const sessionId = cookies.get('session');
	if (sessionId) {
		invalidateSession(sessionId);
		cookies.delete('session', { path: '/' });
	}
	throw redirect(302, '/login');
};
