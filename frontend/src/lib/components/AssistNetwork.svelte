<script>
	import { t } from '$lib/i18n.svelte.js';

	/**
	 * @type {{
	 *   network: import('$lib/types.js').AssistNetwork,
	 *   playerHref?: (playerId: number) => string
	 * }}
	 */
	let { network, playerHref } = $props();

	const max = $derived(network.links.reduce((m, l) => Math.max(m, l.goals), 0) || 1);
</script>

<section class="card flex flex-col gap-3 bg-base-100 p-5">
	<div>
		<h3 class="font-semibold">{t('stats.assistNetwork')}</h3>
		<p class="hint">{t('stats.assistNetworkHint')}</p>
	</div>

	{#if network.links.length === 0}
		<p class="empty">{t('stats.assistNetworkEmpty')}</p>
	{:else}
		<ul class="links">
			{#each network.links as link (link.assist_player_id + '-' + link.scorer_player_id)}
				<li class="link">
					<span class="names">
						{#if playerHref}
							<a class="link-hover" href={playerHref(link.assist_player_id)}>{link.assist_name}</a>
							<span class="arrow">&rarr;</span>
							<a class="link-hover" href={playerHref(link.scorer_player_id)}>{link.scorer_name}</a>
						{:else}
							{link.assist_name} <span class="arrow">&rarr;</span> {link.scorer_name}
						{/if}
					</span>
					<span class="bar" style="--w: {(link.goals / max) * 100}%"></span>
					<span class="count">{link.goals}</span>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	.hint {
		margin-top: 3px;
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.links {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.link {
		display: grid;
		grid-template-columns: minmax(9rem, auto) 1fr auto;
		align-items: center;
		gap: 10px;
		font-size: 0.84rem;
	}
	.names {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.arrow {
		margin: 0 3px;
		color: var(--ink-muted);
	}
	.bar {
		height: 8px;
		border-radius: 4px;
		background: linear-gradient(
			to right,
			var(--color-primary) var(--w),
			color-mix(in oklch, var(--color-base-content) 8%, transparent) var(--w)
		);
	}
	.count {
		font-variant-numeric: tabular-nums;
		font-weight: 700;
		min-width: 1.5rem;
		text-align: right;
	}
	.empty {
		padding: 20px 0;
		text-align: center;
		font-size: 0.86rem;
		color: var(--ink-muted);
	}
</style>
