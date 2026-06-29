<script lang="ts">
	import { fly } from 'svelte/transition';
	let { form } = $props();
</script>

<svelte:head>
	<title>Sign In - Cogneva</title>
</svelte:head>

<div class="page-bg">
	<div class="light-ray"></div>
	
	<div class="container" in:fly={{ y: 30, duration: 800, delay: 150 }}>
		<div class="auth-card">
			<div class="header">
				<h1 class="title">Sign In</h1>
				<p class="subtitle">Please enter your details to sign in.</p>
			</div>
			
			<form method="POST">
				{#if form?.error}
					<div class="error">{form.error}</div>
				{/if}
				
				<div class="field">
					<input type="text" id="username" name="username" required placeholder="Enter your username"/>
				</div>
				
				<div class="field">
					<input type="password" id="password" name="password" required placeholder="Password"/>
				</div>
				
				<div class="forgot-wrapper">
					<a href="/login" class="forgot-link">Forgot Password?</a>
				</div>
				
				<button type="submit" class="btn-submit">Sign in</button>
			</form>
			
			<p class="switch-link">
				Don't have an account? <a href="/signup">Sign up</a>
			</p>
		</div>
	</div>
</div>

<style>
	:global(body) {
		margin: 0;
		background: #000000;
	}

	.page-bg {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: #000000;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		font-family: 'Inter', system-ui, sans-serif;
	}
	
	.light-ray {
		position: absolute;
		top: -20%;
		right: -10%;
		width: 60%;
		height: 140%;
		background: linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0) 50%);
		transform: rotate(35deg);
		pointer-events: none;
		filter: blur(60px);
		z-index: 0;
	}

	.container {
		position: relative;
		z-index: 10;
		width: 100%;
		display: flex;
		justify-content: center;
		padding: 2rem;
	}
	
	.auth-card {
		width: 100%;
		max-width: 400px;
		padding: 3rem 2.5rem;
		border-radius: 24px;
		background: rgba(255, 255, 255, 0.03);
		backdrop-filter: blur(20px);
		-webkit-backdrop-filter: blur(20px);
		border: 1px solid rgba(255, 255, 255, 0.05);
		box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
	}

	.header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.title {
		margin: 0 0 0.5rem 0;
		font-size: 1.5rem;
		font-weight: 600;
		color: #FFFFFF;
		font-family: 'Outfit', sans-serif;
	}

	.subtitle {
		margin: 0;
		font-size: 0.875rem;
		color: rgba(255, 255, 255, 0.6);
	}

	.error {
		background: rgba(239, 68, 68, 0.1);
		color: #ef4444;
		padding: 0.75rem;
		border-radius: 8px;
		margin-bottom: 1rem;
		font-size: 0.875rem;
		text-align: center;
	}

	.field {
		margin-bottom: 1rem;
	}

	input {
		width: 100%;
		padding: 1rem 1.25rem;
		border-radius: 12px;
		border: 1px solid rgba(255, 255, 255, 0.05);
		background: rgba(255, 255, 255, 0.05);
		color: #FFFFFF;
		font-size: 0.9rem;
		outline: none;
		transition: all 0.2s;
	}

	input::placeholder {
		color: rgba(255, 255, 255, 0.4);
	}

	input:focus {
		background: rgba(255, 255, 255, 0.08);
		border-color: rgba(255, 255, 255, 0.15);
	}

	.forgot-wrapper {
		text-align: right;
		margin-bottom: 2rem;
	}

	.forgot-link {
		color: rgba(255, 255, 255, 0.6);
		font-size: 0.75rem;
		text-decoration: none;
		transition: color 0.2s;
	}

	.forgot-link:hover {
		color: #FFFFFF;
	}

	.btn-submit {
		width: 100%;
		padding: 1rem;
		border-radius: 12px;
		background: #FFFFFF;
		color: #000000;
		font-weight: 600;
		font-size: 1rem;
		border: none;
		cursor: pointer;
		transition: transform 0.2s, background 0.2s;
	}

	.btn-submit:hover {
		background: #F0F0F0;
		transform: translateY(-1px);
	}

	.switch-link {
		margin-top: 2rem;
		text-align: center;
		font-size: 0.8rem;
		color: rgba(255, 255, 255, 0.6);
	}

	.switch-link a {
		color: #FFFFFF;
		text-decoration: none;
		font-weight: 500;
	}
</style>
