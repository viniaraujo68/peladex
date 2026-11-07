<script>
	import { t } from '$lib/i18n.svelte.js';
	import FormDots from './FormDots.svelte';

	/**
	 * @type {{
	 *   left: import('$lib/types.js').PlayerRow,
	 *   right: import('$lib/types.js').PlayerRow,
	 *   lines: import('$lib/compareLines.js').CompareLine[],
	 *   showForm: boolean,
	 *   playerHref: (playerId: number) => string
	 * }}
	 */
	let { left, right, lines, showForm, playerHref } = $props();
</script>

<div class="line head">
	<a class="side left name link-hover" href={playerHref(left.player_id)}>{left.name}</a>
	<span class="mid"></span>
	<a class="side right name link-hover" href={playerHref(right.player_id)}>{right.name}</a>
</div>
{#each lines as line (line.label)}
	<div class="line">
		<span class="side left">
			<span class="value" class:win={line.winner === 'a'}>{line.left}</span>
			<span class="bar"><i style="width: {line.leftWidth}%" class:win={line.winner === 'a'}></i></span>
		</span>
		<span class="mid">{line.label}</span>
		<span class="side right">
			<span class="bar"><i style="width: {line.rightWidth}%" class:win={line.winner === 'b'}></i></span>
			<span class="value" class:win={line.winner === 'b'}>{line.right}</span>
		</span>
	</div>
{/each}
{#if showForm}
	<div class="line">
		<span class="side left"><FormDots form={left.recent_form} /></span>
		<span class="mid">{t('ranking.form')}</span>
		<span class="side right"><FormDots form={right.recent_form} /></span>
	</div>
{/if}

<style>
	.line {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 136px minmax(0, 1fr);
		align-items: center;
		gap: 12px;
		padding: 4px 0;
	}
	.line.head {
		padding-bottom: 8px;
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 9%, transparent);
	}
	.name {
		font-weight: 700;
		font-size: 1.05rem;
	}
	.side {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}
	.side.left {
		justify-content: flex-end;
	}
	.mid {
		font-size: 0.72rem;
		text-align: center;
		color: var(--ink-muted);
	}
	.value {
		min-width: 3.2em;
		font-variant-numeric: tabular-nums;
		font-weight: 500;
	}
	.side.left .value {
		text-align: right;
	}
	.value.win {
		font-weight: 700;
		color: var(--ink-primary);
	}
	.bar {
		display: flex;
		flex: 1;
		height: 8px;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 7%, transparent);
		overflow: hidden;
	}
	.side.left .bar {
		justify-content: flex-end;
	}
	.bar i {
		display: block;
		height: 100%;
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-base-content) 30%, transparent);
	}
	.bar i.win {
		background: var(--color-primary);
	}
	@media (max-width: 560px) {
		.line {
			grid-template-columns: minmax(0, 1fr) 88px minmax(0, 1fr);
			gap: 6px;
		}
		.mid {
			font-size: 0.66rem;
			overflow-wrap: anywhere;
		}
		.bar {
			display: none;
		}
	}
</style>
