import { fail, redirect } from '@sveltejs/kit';
import { db_instance } from '$lib/server/db';
import { createSession } from '$lib/server/auth';
import bcrypt from 'bcryptjs';

export const actions = {
	default: async ({ request, cookies }) => {
		const data = await request.formData();
		const username = data.get('username') as string;
		const password = data.get('password') as string;

		if (!username || !password) {
			return fail(400, { error: 'Missing username or password' });
		}

		const user = db_instance.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;

		if (!user || !(await bcrypt.compare(password, user.password_hash))) {
			return fail(400, { error: 'Invalid username or password' });
		}

		const session = createSession(user.id);
		cookies.set('session', session.id, {
			path: '/',
			httpOnly: true,
			sameSite: 'lax',
			secure: process.env.NODE_ENV === 'production'
		});

		throw redirect(302, '/');
	}
};
