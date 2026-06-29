import { db_instance } from './db';
import crypto from 'crypto';

export function createSession(userId: string) {
	const sessionId = crypto.randomBytes(32).toString('hex');
	const expiresAt = Date.now() + 1000 * 60 * 60 * 24 * 30; // 30 days
	
	const stmt = db_instance.prepare('INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, ?)');
	stmt.run(sessionId, userId, expiresAt);
	
	return { id: sessionId, userId, expiresAt };
}

export function validateSession(sessionId: string) {
	const stmt = db_instance.prepare(`
		SELECT sessions.id, sessions.user_id, sessions.expires_at, users.username 
		FROM sessions 
		JOIN users ON sessions.user_id = users.id 
		WHERE sessions.id = ?
	`);
	const session = stmt.get(sessionId) as any;
	
	if (!session) return null;
	if (Date.now() >= session.expires_at) {
		db_instance.prepare('DELETE FROM sessions WHERE id = ?').run(sessionId);
		return null;
	}
	
	// Extend session by 30 days if less than 15 days left
	if (Date.now() >= session.expires_at - 1000 * 60 * 60 * 24 * 15) {
		const newExpiresAt = Date.now() + 1000 * 60 * 60 * 24 * 30;
		db_instance.prepare('UPDATE sessions SET expires_at = ? WHERE id = ?').run(newExpiresAt, sessionId);
		session.expires_at = newExpiresAt;
	}
	
	return session;
}

export function invalidateSession(sessionId: string) {
	db_instance.prepare('DELETE FROM sessions WHERE id = ?').run(sessionId);
}
