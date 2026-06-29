import { fail, redirect } from '@sveltejs/kit';
import { db_instance } from '$lib/server/db';
import { createSession } from '$lib/server/auth';
import crypto from 'crypto';
import bcrypt from 'bcryptjs';

export const actions = {
	default: async ({ request, cookies }) => {
		const data = await request.formData();
		const username = data.get('username') as string;
		const password = data.get('password') as string;

		if (!username || !password || username.length < 3 || password.length < 6) {
			return fail(400, { error: 'Username (min 3 chars) and password (min 6 chars) required' });
		}

		const id = crypto.randomUUID();
		const passwordHash = await bcrypt.hash(password, 10);

		try {
			db_instance.prepare('INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)')
				.run(id, username, passwordHash);
		} catch (e: any) {
			if (e.message.includes('UNIQUE')) {
				return fail(400, { error: 'Username already exists' });
			}
			return fail(500, { error: 'Internal error' });
		}

		const session = createSession(id);
		cookies.set('session', session.id, {
			path: '/',
			httpOnly: true,
			sameSite: 'lax',
			secure: process.env.NODE_ENV === 'production'
		});

		throw redirect(302, '/');
	}
};
