<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	let { children } = $props();

	onMount(() => {
		if (!sessionStorage.getItem('app_launched')) {
			sessionStorage.setItem('app_launched', 'true');
			if (window.location.pathname !== '/login' && window.location.pathname !== '/signup') {
				fetch('/logout', { method: 'POST' }).then(() => {
					window.location.href = '/login';
				});
			}
		}
	});
</script>

{@render children()}
