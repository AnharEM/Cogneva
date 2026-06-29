<script lang="ts">
	import { onMount } from "svelte";
	import { fly, fade } from "svelte/transition";
	import { User, LogOut, Send, Bot, Moon, Sun, Menu, Plus, Stethoscope, Edit2, Trash2, Brain, Leaf } from "@lucide/svelte";

	let { data } = $props();

	type Message = { role: string; content: string; created_at?: string; timestamp?: string };
	type ChatSession = { id: string; title: string; messages: Message[] };

	let sessions = $state<ChatSession[]>([]);
	let activeSessionId = $state<string>("");

	let editingSessionId = $state<string | null>(null);
	let editTitle = $state("");

	let messages = $derived(sessions.find(s => s.id === activeSessionId)?.messages || []);
	let userInput = $state("");
	let isLoading = $state(false);
	let theme = $state("dark"); 
	let showDeleteModal = $state(false);
	let sidebarOpen = $state(true);
	let chatContainer: HTMLElement;

	onMount(async () => {
		const savedTheme = localStorage.getItem("theme");
		if (savedTheme) {
			setTheme(savedTheme);
		} else {
			setTheme(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
		}

		// Fetch all sessions from backend
		try {
			const sessionRes = await fetch("/api/chat/sessions");
			if (sessionRes.ok) {
				const backendSessions = await sessionRes.json();
				if (Array.isArray(backendSessions) && backendSessions.length > 0) {
					sessions = backendSessions.map((s: any) => ({ ...s, messages: [] }));
				} else {
					sessions = [{ id: data.user.id, title: "Primary Session", messages: [] }];
				}
			} else {
				sessions = [{ id: data.user.id, title: "Primary Session", messages: [] }];
			}
			activeSessionId = sessions[0].id;
			
			await loadHistory(activeSessionId);
		} catch (e) {
			console.error("Failed to load sessions", e);
		}
	});

	async function loadHistory(sessionId: string) {
		try {
			const res = await fetch(`/api/chat/history?session_id=${sessionId}`);
			if (res.ok) {
				const history = await res.json();
				const session = sessions.find(s => s.id === sessionId);
				if (session) {
					if (Array.isArray(history) && history.length > 0) {
						session.messages = history.map((m: any) => ({
							...m,
							timestamp: m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ""
						}));
					} else {
						session.messages = [
							{ role: "ai", content: `Hello there. I'm Dr. Eva, your AI Psychologist. This is a safe, completely private space for you to share whatever is on your mind. To start, what name would you prefer I use for you?`, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) },
						];
					}
					scrollToBottom();
				}
			}
		} catch (e) {
			console.error("Failed to load history", e);
		}
	}

	function setTheme(t: string) {
		theme = t;
		localStorage.setItem("theme", t);
		if (t === "light") document.documentElement.classList.remove("dark");
		else document.documentElement.classList.add("dark");
	}
	
	function toggleTheme() {
		setTheme(theme === 'light' ? 'dark' : 'light');
	}

	async function sendMessage() {
		if (!userInput.trim() || isLoading) return;

		const currentInput = userInput.trim();
		const session = sessions.find(s => s.id === activeSessionId);
		if (!session) return;

		const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

		// Dynamically rename the session if this is the first user message
		if (session.messages.length <= 1 && (session.title.startsWith("Session ") || session.title === "Primary Session" || session.title === "Legacy Session" || session.title === "Therapy Session")) {
			session.title = currentInput.slice(0, 25) + (currentInput.length > 25 ? "..." : "");
			fetch(`/api/chat/sessions/${session.id}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ title: session.title })
			}).catch(e => console.error("Failed to auto-rename", e));
		}

		session.messages = [...session.messages, { role: "user", content: currentInput, timestamp: timeNow }];
		userInput = "";
		isLoading = true;

		scrollToBottom();

		try {
			const res = await fetch("/api/chat", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ 
					user_id: data.user.id,
					session_id: activeSessionId,
					user_input: currentInput 
				}),
			});

			if (res.ok) {
				const responseData = await res.json();
				const s = sessions.find(s => s.id === activeSessionId);
				if (s) s.messages = [...s.messages, { role: "ai", content: responseData.response, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }];
			} else {
				const s = sessions.find(s => s.id === activeSessionId);
				if (s) s.messages = [...s.messages, { role: "ai", content: "Sorry, I am having trouble connecting to the server.", timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }];
			}
		} catch (e) {
			const s = sessions.find(s => s.id === activeSessionId);
			if (s) s.messages = [...s.messages, { role: "ai", content: "Connection error.", timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }];
		} finally {
			isLoading = false;
			scrollToBottom();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}

	function scrollToBottom() {
		setTimeout(() => {
			if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
		}, 50);
	}

	function startNewSession() {
		const newId = crypto.randomUUID();
		sessions = [
			{ 
				id: newId, 
				title: `Session ${sessions.length + 1}`, 
				messages: [{ role: "ai", content: "Hello there. I'm Dr. Eva, your AI Psychologist. This is a safe, completely private space for you to share whatever is on your mind. To start, what name would you prefer I use for you?", timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]
			},
			...sessions
		];
		activeSessionId = newId;
		if (window.innerWidth < 768) {
			sidebarOpen = false;
		}
		scrollToBottom();
	}

	function switchSession(id: string) {
		activeSessionId = id;
		const session = sessions.find(s => s.id === id);
		if (session && session.messages.length === 0) {
			loadHistory(id);
		}
		if (window.innerWidth < 768) {
			sidebarOpen = false;
		}
		scrollToBottom();
	}

	function startEdit(session: ChatSession) {
		editingSessionId = session.id;
		editTitle = session.title;
	}

	async function saveEdit() {
		if (editingSessionId) {
			const s = sessions.find(s => s.id === editingSessionId);
			if (s && editTitle.trim() && s.title !== editTitle.trim()) {
				s.title = editTitle.trim();
				try {
					await fetch(`/api/chat/sessions/${editingSessionId}`, {
						method: 'PUT',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({ title: s.title })
					});
				} catch (e) {
					console.error("Failed to rename session", e);
				}
			}
			editingSessionId = null;
		}
	}

	async function deleteSession(id: string) {
		sessions = sessions.filter(s => s.id !== id);
		try {
			await fetch(`/api/chat/sessions/${id}`, { method: 'DELETE' });
		} catch (e) {
			console.error("Failed to delete session", e);
		}
		
		if (sessions.length === 0) {
			startNewSession();
		} else if (activeSessionId === id) {
			activeSessionId = sessions[0].id;
			if (sessions[0].messages.length === 0) {
				loadHistory(activeSessionId);
			}
		}
	}

	function focus(node: HTMLElement) {
		node.focus();
	}
</script>

<svelte:head>
	<title>Cogneva - AI Psychologist</title>
</svelte:head>

<div class="app-layout">
	<!-- Background Atmospheric Glow -->
	<div class="radial-glow"></div>

	<!-- Sidebar Overlay -->
	{#if sidebarOpen}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="sidebar-backdrop" onclick={() => sidebarOpen = false} in:fade={{duration: 200}} out:fade={{duration: 200}}></div>
	{/if}

	<aside class="sidebar glass" class:open={sidebarOpen}>
		<div class="sidebar-header">
			<div class="logo">
				<div class="logo-icon"><div class="logo-dot"></div></div>
				<h2 class="brand-text">Cogneva</h2>
			</div>
		</div>
		<div class="sidebar-content">
			<button class="new-session-btn" onclick={startNewSession}>
				<Plus size={16} strokeWidth={2.5} /> <span style="font-weight: 500; font-size: 0.9rem;">New session</span>
			</button>
			<div class="sessions-list">
				<div class="sessions-label">Recent Sessions</div>
				{#each sessions as session (session.id)}
					<div class="session-wrapper {activeSessionId === session.id ? 'active' : ''}">
						<button 
							class="nav-item" 
							onclick={() => switchSession(session.id)}
						>
							{#if activeSessionId === session.id}
								<Brain size={18} />
							{:else}
								<Leaf size={18} />
							{/if}
							{#if editingSessionId === session.id}
								<input 
									class="edit-input"
									bind:value={editTitle} 
									onkeydown={(e) => { if(e.key === 'Enter') saveEdit(); }}
									onblur={saveEdit}
									use:focus
									onclick={(e) => e.stopPropagation()}
								/>
							{:else}
								<span class="session-title">{session.title}</span>
							{/if}
						</button>
						<div class="session-actions">
							<button class="action-btn" onclick={(e) => { e.stopPropagation(); startEdit(session); }} aria-label="Rename session"><Edit2 size={14} /></button>
							<button class="action-btn delete" onclick={(e) => { e.stopPropagation(); deleteSession(session.id); }} aria-label="Delete session"><Trash2 size={14} /></button>
						</div>
					</div>
				{/each}
			</div>
		</div>
		<div class="sidebar-footer">
			<div class="user-profile">
				<div class="avatar"><User size={20} /></div>
				<div class="user-info">
					<span class="username">{data.user.username}</span>
				</div>
				<form method="POST" action="/logout">
					<button class="logout-btn" title="Log out" aria-label="Log out"><LogOut size={18} /></button>
				</form>
				<button type="button" class="logout-btn delete-account-btn" title="Delete Account" aria-label="Delete Account" onclick={() => showDeleteModal = true}>
					<Trash2 size={18} />
				</button>
			</div>
		</div>
	</aside>

	<main class="chat-area">
		<!-- Top Navigation Bar -->
		<header class="top-nav glass">
			<button class="icon-btn" onclick={() => sidebarOpen = !sidebarOpen} aria-label="Toggle Sidebar">
				<Menu size={24} />
			</button>
			
			<div class="nav-center">
				<h1 class="nav-title">Cogneva</h1>
				<div class="status-indicator">
					<span class="status-dot"></span>
					<span class="status-text">ACTIVE SESSION</span>
				</div>
			</div>
			
			<div class="nav-right" style="display: flex; gap: 0.75rem; align-items: center;">
				<button class="theme-pill" onclick={toggleTheme} aria-label="Toggle Theme" class:dark={theme === 'dark'}>
					<div class="theme-knob">
						{#if theme === 'light'}
							<Sun size={14} />
						{:else}
							<Moon size={14} />
						{/if}
					</div>
				</button>
			</div>
		</header>

		<div class="messages" bind:this={chatContainer}>
			{#each messages as msg, i (i)}
				<div class="message-row {msg.role}" in:fly={{ y: 20, duration: 400, delay: 50 }}>
					{#if msg.role === 'ai'}
					<div class="ai-avatar-wrapper">
						<div class="ai-avatar"><Stethoscope size={18} /></div>
					</div>
					{/if}
					<div class="message-content-wrapper {msg.role}">
						{#if msg.role === 'ai'}
							<div class="ai-name">DR. EVA</div>
						{/if}
						<div class="message-bubble {msg.role}">
							<div class="msg-content">{msg.content}</div>
							{#if msg.timestamp}
								<div class="msg-time">{msg.timestamp}</div>
							{/if}
						</div>
					</div>
				</div>
			{/each}

			{#if isLoading}
				<div class="message-row ai" in:fade={{ duration: 200 }}>
					<div class="ai-avatar-wrapper">
						<div class="ai-avatar"><Stethoscope size={18} /></div>
					</div>
					<div class="message-content-wrapper ai">
						<div class="ai-name">DR. EVA</div>
						<div class="message-bubble ai typing">
							<div class="typing-indicator">
								<span></span><span></span><span></span>
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Floating Conversational Input Dock -->
		<div class="input-dock-container">
			<div class="input-dock glass">
				<textarea
					bind:value={userInput}
					onkeydown={handleKeydown}
					placeholder="Type your mind here..."
					rows="1"
				></textarea>
				<button class="send-btn" onclick={sendMessage} disabled={isLoading || !userInput.trim()} aria-label="Send message">
					<Send size={18} />
				</button>
			</div>
		</div>
	</main>

	{#if showDeleteModal}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="modal-backdrop" onclick={() => showDeleteModal = false} in:fade={{duration: 150}} out:fade={{duration: 150}}>
			<div class="modal-container glass" onclick={(e) => e.stopPropagation()}>
				<div class="modal-header">
					<h3>Delete Account?</h3>
				</div>
				<div class="modal-body">
					<p>Are you absolutely sure you want to permanently delete your account and all history? This action cannot be undone.</p>
				</div>
				<div class="modal-footer">
					<button class="btn-cancel" onclick={() => showDeleteModal = false}>Cancel</button>
					<form method="POST" action="/delete-account">
						<button type="submit" class="btn-danger">Yes, Delete Everything</button>
					</form>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.app-layout {
		display: flex;
		height: 100vh;
		width: 100vw;
		overflow: hidden;
		position: relative;
	}

	.radial-glow {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: var(--glow-bg);
		pointer-events: none;
		z-index: 0;
		transition: background 0.5s ease;
	}

	:global(.dark) .radial-glow {
		background: var(--glow-bg-dark);
	}

	.sidebar-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.4);
		z-index: 20;
		backdrop-filter: blur(4px);
		-webkit-backdrop-filter: blur(4px);
	}

	.sidebar {
		position: fixed;
		top: 0;
		left: -320px;
		width: 320px;
		height: 100%;
		display: flex;
		flex-direction: column;
		border-right: 1px solid var(--border);
		z-index: 30;
		transition: left 0.4s cubic-bezier(0.4, 0, 0.2, 1);
		background: var(--bg-secondary);
	}

	.sidebar.open {
		left: 0;
	}

	.sidebar-header {
		padding: 1.5rem;
		border-bottom: 1px solid var(--border);
	}

	.logo {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.logo-icon {
		width: 20px;
		height: 20px;
		border-radius: 50%;
		border: 2px solid var(--fg);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.logo-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background-color: var(--fg);
	}

	.logo h2 {
		margin: 0;
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--fg);
		font-family: 'Times New Roman', Times, serif;
	}

	.new-session-btn {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem;
		border-radius: 8px;
		background: transparent;
		border: 1px solid var(--border);
		color: var(--fg-muted);
		font-weight: 500;
		margin-bottom: 1.5rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.new-session-btn:hover {
		background: var(--bg-secondary);
		border-color: var(--border);
		color: var(--fg);
	}

	.sidebar-content {
		flex: 1;
		padding: 1.5rem 1rem;
		overflow-y: auto;
	}

	.sessions-label {
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--fg-muted);
		margin: 1rem 0 0.5rem 0.5rem;
		font-weight: 600;
	}

	.sessions-list {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.session-wrapper {
		position: relative;
		border-radius: 12px;
		transition: all 0.2s;
		border: 1px solid transparent;
		background: transparent;
	}

	.session-wrapper:hover {
		background: var(--bg);
		border-color: var(--border);
	}

	.session-wrapper.active {
		background: var(--bg);
		border-color: var(--border);
		box-shadow: 0 2px 10px rgba(0,0,0,0.02);
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.875rem 1rem;
		cursor: pointer;
		color: var(--fg-muted);
		font-weight: 500;
		width: 100%;
		border: none;
		background: transparent;
		text-align: left;
	}

	.session-wrapper.active .nav-item {
		color: var(--fg);
	}

	.session-title {
		flex: 1;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		padding-right: 30px;
	}

	.edit-input {
		flex: 1;
		background: var(--bg);
		border: 1px solid var(--brand);
		color: var(--fg);
		border-radius: 4px;
		padding: 0.25rem 0.5rem;
		font-size: 0.9rem;
		outline: none;
	}

	.edit-input:focus, .edit-input:focus-visible {
		box-shadow: none !important;
		outline: none !important;
	}

	.session-actions {
		position: absolute;
		right: 0.5rem;
		top: 50%;
		transform: translateY(-50%);
		display: flex;
		gap: 0.25rem;
		opacity: 0;
		transition: opacity 0.2s;
	}

	.session-wrapper:hover .session-actions,
	.session-wrapper.active .session-actions {
		opacity: 1;
	}

	.action-btn {
		padding: 4px;
		border-radius: 4px;
		color: var(--fg-muted);
		background: var(--bg-secondary);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.action-btn:hover {
		color: var(--fg);
		background: var(--border);
	}

	.action-btn.delete:hover {
		color: #EF4444;
		background: rgba(239, 68, 68, 0.1);
	}

	.sidebar-footer {
		padding: 1.5rem 1rem;
		border-top: 1px solid var(--border);
	}

	.user-profile {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.avatar {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: rgba(99, 85, 217, 0.1);
		color: var(--brand);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.user-info {
		flex: 1;
		overflow: hidden;
	}

	.username {
		display: block;
		font-weight: 600;
		font-size: 0.9rem;
		color: var(--fg);
		white-space: nowrap;
		text-overflow: ellipsis;
		overflow: hidden;
	}

	.logout-btn {
		color: var(--fg-muted);
		padding: 0.5rem;
		border-radius: 8px;
	}

	.logout-btn:hover, .delete-account-btn:hover {
		background: rgba(239, 68, 68, 0.1);
		color: #EF4444;
	}

	.chat-area {
		flex: 1;
		display: flex;
		flex-direction: column;
		position: relative;
		z-index: 1;
	}

	.top-nav {
		padding: 1rem 1.5rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-bottom: 1px solid var(--border);
		background: var(--glass-bg);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
		z-index: 10;
	}

	.nav-center {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
	}

	.nav-title {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--fg);
		letter-spacing: -0.01em;
		font-family: 'Times New Roman', Times, serif;
	}

	.theme-pill {
		width: 52px;
		height: 28px;
		border-radius: 14px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		position: relative;
		padding: 0;
		display: flex;
		align-items: center;
		cursor: pointer;
	}

	.theme-knob {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: var(--brand);
		color: var(--bg);
		display: flex;
		align-items: center;
		justify-content: center;
		position: absolute;
		left: 2px;
		transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}

	.theme-pill.dark .theme-knob {
		left: calc(100% - 24px);
	}

	.status-indicator {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: 2px;
	}

	.status-dot {
		width: 6px;
		height: 6px;
		background-color: var(--brand);
		border-radius: 50%;
		animation: pulse-soft 3s infinite ease-in-out;
	}
	
	:global(.dark) .status-dot {
		background-color: var(--brand);
	}

	.status-text {
		font-size: 0.75rem;
		color: var(--fg-muted);
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.icon-btn {
		color: var(--fg-muted);
		padding: 0.5rem;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.icon-btn:hover {
		color: var(--fg);
		background: var(--border);
	}

	.messages {
		flex: 1;
		overflow-y: auto;
		padding: 2rem 1rem 8rem 1rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		scroll-behavior: smooth;
		max-width: 900px;
		margin: 0 auto;
		width: 100%;
	}

	.message-row {
		display: flex;
		width: 100%;
		gap: 1rem;
		margin-bottom: 0.5rem;
	}

	.message-row.user {
		justify-content: flex-end;
	}

	.message-row.ai {
		justify-content: flex-start;
	}

	.ai-avatar-wrapper {
		display: flex;
		align-items: flex-start;
		margin-top: 1.5rem;
	}

	.ai-avatar {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--fg-muted);
	}

	.message-content-wrapper {
		display: flex;
		flex-direction: column;
		max-width: 80%;
	}

	.message-content-wrapper.user {
		align-items: flex-end;
	}

	.message-content-wrapper.ai {
		align-items: flex-start;
	}

	.ai-name {
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--fg-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 0.5rem;
		margin-left: 0.25rem;
	}

	.message-bubble {
		padding: 1rem 1.25rem;
		font-size: 0.95rem;
		line-height: 1.6;
		box-shadow: 0 4px 20px -5px rgba(0,0,0,0.05);
	}

	.message-bubble.user {
		background: #111;
		color: #fff;
		border-radius: 20px;
		border-bottom-right-radius: 4px;
	}

	:global(.dark) .message-bubble.user {
		background: #fff;
		color: #111;
	}

	.message-bubble.ai {
		background: var(--bg-secondary);
		color: var(--fg);
		border-radius: 20px;
		border-bottom-left-radius: 4px;
		border: 1px solid var(--border);
	}

	.msg-content {
		white-space: pre-wrap;
		word-break: break-word;
	}

	.msg-time {
		font-size: 0.65rem;
		margin-top: 0.5rem;
		opacity: 0.6;
		text-align: left;
		user-select: none;
	}

	.input-dock-container {
		position: absolute;
		bottom: 2rem;
		left: 0;
		right: 0;
		display: flex;
		justify-content: center;
		padding: 0 1.5rem;
		z-index: 10;
		pointer-events: none;
	}

	.input-dock {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		background: var(--glass-bg);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
		border: 1px solid var(--glass-border);
		border-radius: 50px;
		padding: 0.75rem 0.75rem 0.75rem 1rem;
		width: 100%;
		max-width: 800px;
		box-shadow: 0 10px 40px -10px rgba(0,0,0,0.1), 0 0 0 1px rgba(255,255,255,0.05);
		pointer-events: auto;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.input-dock:focus-within {
		transform: translateY(-2px);
		box-shadow: 0 15px 50px -10px rgba(0,0,0,0.15), 0 0 0 1px var(--brand);
	}

	.utility-btn {
		color: var(--fg-muted);
		padding: 0.5rem;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.utility-btn:hover {
		color: var(--fg);
		background: var(--border);
	}

	textarea {
		flex: 1;
		background: transparent;
		border: none;
		color: var(--fg);
		font-family: inherit;
		font-size: 1rem;
		resize: none;
		padding: 0.5rem 0;
		outline: none;
		max-height: 120px;
		min-height: 24px;
	}

	textarea:focus, textarea:focus-visible {
		border: none !important;
		box-shadow: none !important;
		background: transparent !important;
	}

	textarea::placeholder {
		color: var(--fg-muted);
		opacity: 0.7;
	}

	.send-btn {
		background: var(--brand);
		color: var(--bg);
		width: 44px;
		height: 44px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
	}

	.send-btn:hover:not(:disabled) {
		background: var(--brand-hover);
		transform: scale(1.05);
		box-shadow: 0 4px 15px rgba(99, 85, 217, 0.4);
	}

	.send-btn:disabled {
		opacity: 0.5;
		background: var(--fg-muted);
		cursor: not-allowed;
	}

	.typing-indicator {
		display: flex;
		align-items: center;
		gap: 4px;
		height: 24px;
		padding: 0 0.5rem;
	}

	.typing-indicator span {
		display: block;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--brand);
		opacity: 0.6;
		animation: typing 1.4s infinite both;
	}

	.typing-indicator span:nth-child(1) { animation-delay: 0s; }
	.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
	.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

	@keyframes typing {
		0%, 80%, 100% { transform: scale(0.8); opacity: 0.4; }
		40% { transform: scale(1.2); opacity: 1; }
	}

	@media (max-width: 768px) {
		.messages {
			padding: 1.5rem 1rem 7rem 1rem;
		}
		.input-dock-container {
			bottom: 1rem;
		}
	}

	@media (min-width: 769px) {
		.sidebar-backdrop {
			display: none;
		}
		
		.sidebar {
			position: relative;
			left: auto;
			margin-left: -320px;
			transition: margin-left 0.4s cubic-bezier(0.4, 0, 0.2, 1);
		}

		.sidebar.open {
			left: auto;
			margin-left: 0;
		}
	}

	/* Hide scrollbars but keep functionality */
	.messages::-webkit-scrollbar, 
	.sidebar-content::-webkit-scrollbar,
	textarea::-webkit-scrollbar {
		display: none;
	}

	.messages, 
	.sidebar-content,
	textarea {
		-ms-overflow-style: none;
		scrollbar-width: none;
	}
	.modal-backdrop {
		position: fixed;
		top: 0; left: 0; right: 0; bottom: 0;
		background: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(8px);
		-webkit-backdrop-filter: blur(8px);
		z-index: 1000;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.modal-container {
		width: 90%;
		max-width: 400px;
		background: var(--glass-bg);
		border: 1px solid var(--border);
		border-radius: 16px;
		padding: 1.5rem;
		box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
		color: var(--fg);
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.modal-header h3 {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 600;
		font-family: 'Times New Roman', Times, serif;
	}

	.modal-body p {
		margin: 0;
		font-size: 0.95rem;
		color: var(--fg-muted);
		line-height: 1.5;
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}

	.btn-cancel, .btn-danger {
		padding: 0.6rem 1rem;
		border-radius: 8px;
		font-weight: 500;
		font-size: 0.9rem;
		cursor: pointer;
		border: none;
		transition: all 0.2s;
	}

	.btn-cancel {
		background: transparent;
		color: var(--fg);
		border: 1px solid var(--border);
	}

	.btn-cancel:hover {
		background: var(--bg-secondary);
	}

	.btn-danger {
		background: #EF4444;
		color: #FFF;
	}

	.btn-danger:hover {
		background: #DC2626;
	}
</style>
