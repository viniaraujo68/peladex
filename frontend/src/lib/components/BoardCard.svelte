<script>
	import { SegmentedControl } from '@viniaraujo68/plinth/components';

	/**
	 * @type {{
	 *   title: string,
	 *   options: { id: string, label: string }[],
	 *   value: string,
	 *   onchange: (id: string) => void,
	 *   empty: string|null,
	 *   controls?: import('svelte').Snippet,
	 *   children: import('svelte').Snippet
	 * }}
	 */
	let { title, options, value, onchange, empty, controls, children } = $props();
</script>

<section class="card flex flex-col gap-4 bg-base-100 p-5">
	<div class="head">
		<h3 class="font-semibold">{title}</h3>
		<div class="tools">
			{@render controls?.()}
			<SegmentedControl {options} {value} label={title} size="sm" {onchange} />
		</div>
	</div>
	{#if empty}
		<p class="empty">{empty}</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="table table-sm">{@render children()}</table>
		</div>
	{/if}
</section>

<style>
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}
	.tools {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 10px;
	}
	.empty {
		padding: 20px 0;
		text-align: center;
		font-size: 0.86rem;
		color: var(--ink-muted);
	}
</style>
