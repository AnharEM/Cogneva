import { redirect } from '@sveltejs/kit';
import { invalidateSession } from '$lib/server/auth';
import { db_instance } from '$lib/server/db';
import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ cookies, locals }) => {
	const user = locals.user;
	if (!user) {
		throw redirect(302, '/login');
	}

    // 1. Delete from PostgreSQL Backend
    try {
        await fetch(`${env.BACKEND_URL}/users/${user.id}`, {
            method: 'DELETE',
            headers: {
                'X-API-Key': env.INTERNAL_API_KEY
            }
        });
    } catch (e) {
        console.error("Failed to delete from backend", e);
    }

	// 2. Clear Session Cookies and all SQLite Sessions
	const sessionId = cookies.get('session');
	if (sessionId) {
		cookies.delete('session', { path: '/' });
	}
	db_instance.prepare('DELETE FROM sessions WHERE user_id = ?').run(user.id);

	// 3. Delete from SQLite Users Table
	db_instance.prepare('DELETE FROM users WHERE id = ?').run(user.id);
	
	throw redirect(302, '/login');
};
