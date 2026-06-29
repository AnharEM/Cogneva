import type { Handle } from '@sveltejs/kit';
import { validateSession } from '$lib/server/auth';

export const handle: Handle = async ({ event, resolve }) => {
	const sessionId = event.cookies.get('session');
	
	if (sessionId) {
		const session = validateSession(sessionId);
		if (session) {
			event.locals.user = { id: session.user_id, username: session.username };
			// Set cookie again to keep it fresh
			event.cookies.set('session', sessionId, {
				path: '/',
				httpOnly: true,
				sameSite: 'lax',
				expires: new Date(session.expires_at),
				secure: process.env.NODE_ENV === 'production'
			});
		} else {
			event.locals.user = null;
			event.cookies.delete('session', { path: '/' });
		}
	} else {
		event.locals.user = null;
	}

	return resolve(event);
};
