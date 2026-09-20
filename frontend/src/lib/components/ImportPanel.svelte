<script>
	import { toast } from '@viniaraujo68/plinth/toast';
	import { post, errorMessage } from '$lib/http.js';
	import { formatMatchdayDate, formatRate } from '$lib/format.svelte.js';
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';

	/**
	 * @type {{
	 *   groupId: number|string,
	 *   onimported: (result: { created: number, replaced: number }) => void
	 * }}
	 */
	let { groupId, onimported } = $props();

	const TEMPLATE = `16/09/2026 @ Campo do Ze

BRANCO: golin, galetti, galo, rick, palma, disciplina, mini
VERMELHO: vini, bamma, breno, igor, rod kauer, cesar, beat
AZUL: ney, rod, lusca, pipi, nona, cop, guarino

VERMELHO 0x0 AZUL
BRANCO 0x0 AZUL
BRANCO 1x0 VERMELHO: golin (galetti)
BRANCO 2x0 AZUL: golin, galo (golin)
BRANCO 0x0 VERMELHO
VERMELHO 0x0 AZUL
AZUL 0x1 BRANCO: disciplina
BRANCO 1x1 VERMELHO: golin (mini), vini

MVP: golin`;

	let text = $state('');
	let checking = $state(false);
	let committing = $state(false);
	let replaceExisting = $state(false);
	let error = $state('');
	let preview = $state(
		/** @type {import('$lib/types.js').ImportPreview|null} */ (null)
	);
	let fileInput = $state(/** @type {HTMLInputElement|undefined} */ (undefined));

	const errors = $derived(preview ? preview.issues.filter((i) => i.severity === 'error') : []);
	const warnings = $derived(preview ? preview.issues.filter((i) => i.severity === 'warning') : []);
	const existingCount = $derived(
		preview ? preview.matchdays.filter((m) => m.already_exists).length : 0
	);
	const canCommit = $derived(
		!!preview && preview.ok && preview.matchdays.length > 0 && (existingCount === 0 || replaceExisting)
	);

	$effect(() => {
		text;
		preview = null;
		error = '';
	});

	async function check() {
		if (!text.trim()) {
			error = t('import.nothing');
			return;
		}
		checking = true;
		error = '';
		try {
			preview = await post(`/groups/${groupId}/import/preview`, { text });
		} catch (e) {
			error = errorMessage(e);
			preview = null;
		} finally {
			checking = false;
		}
	}

	async function commit() {
		committing = true;
		error = '';
		try {
			const result = await post(`/groups/${groupId}/import`, {
				text,
				create_missing_players: true,
				replace_existing: replaceExisting
			});
			toast.success(t('toast.imported'));
			onimported({
				created: result.created_matchday_ids.length,
				replaced: result.replaced
			});
		} catch (e) {
			error = errorMessage(e);
		} finally {
			committing = false;
		}
	}

	/** @param {Event} ev */
	async function onFile(ev) {
		const input = /** @type {HTMLInputElement} */ (ev.currentTarget);
		const file = input.files?.[0];
		if (!file) return;
		text = await file.text();
		input.value = '';
	}

	async function copyTemplate() {
		try {
			await navigator.clipboard.writeText(TEMPLATE);
			toast.success(t('toast.templateCopied'));
		} catch {
			toast.error(t('toast.copyFailed'));
		}
	}
</script>

<div class="import">
	<section class="card flex flex-col gap-4 bg-base-100 p-5">
		<p class="text-sm text-base-content/80">{t('import.subtitle')}</p>

		<div class="block">
			<label class="blabel" for="import-text">{t('import.paste')}</label>
			<textarea
				id="import-text"
				class="textarea notes w-full"
				rows="12"
				spellcheck="false"
				placeholder={t('import.placeholder')}
				bind:value={text}
			></textarea>
		</div>

		<div class="actions">
			<button class="btn btn-primary" disabled={checking || !text.trim()} onclick={check}>
				{checking ? t('import.previewing') : t('import.preview')}
			</button>
			<button class="btn" onclick={() => fileInput?.click()}>
				<Icon name="upload" class="size-4" />
				{t('import.upload')}
			</button>
			<input
				bind:this={fileInput}
				class="hidden"
				type="file"
				accept=".txt,text/plain"
				onchange={onFile}
			/>
			<button class="btn btn-ghost" onclick={() => (text = TEMPLATE)}>
				{t('import.useExample')}
			</button>
			{#if text}
				<button class="btn btn-ghost" onclick={() => (text = '')}>{t('import.clear')}</button>
			{/if}
		</div>

		{#if error}
			<div class="alert alert-soft alert-error">{error}</div>
		{/if}
	</section>

	{#if preview}
		<section class="card flex flex-col gap-4 bg-base-100 p-5">
			<div class="sum">
				<span class="badge badge-soft">
					{t('import.matchdayCount', { count: preview.matchdays.length })}
				</span>
				{#if errors.length}
					<span class="badge badge-soft badge-error">
						{t('import.errorCount', { count: errors.length })}
					</span>
				{/if}
				{#if warnings.length}
					<span class="badge badge-soft badge-warning">
						{t('import.warningCount', { count: warnings.length })}
					</span>
				{/if}
				{#if !errors.length && !warnings.length}
					<span class="badge badge-soft badge-success">
						<Icon name="check" />
						{t('import.noIssues')}
					</span>
				{/if}
			</div>

			{#if preview.issues.length}
				<ul class="issues">
					{#each preview.issues as issue, index (index)}
						<li class="issue" class:err={issue.severity === 'error'}>
							<Icon name="warning" class="size-4 shrink-0" />
							<span class="imsg">
								{#if issue.line > 0}
									<b>{t('import.line', { line: issue.line })}</b>
								{/if}
								{issue.message}
								{#if issue.text}<code>{issue.text}</code>{/if}
							</span>
						</li>
					{/each}
				</ul>
			{/if}

			{#if errors.length}
				<p class="text-sm text-error">{t('import.blockedByErrors')}</p>
			{:else if warnings.length}
				<p class="text-sm text-[var(--ink-warning)]">{t('import.warningsOk')}</p>
			{/if}

			<div class="block">
				<span class="blabel">{t('import.newPlayers')}</span>
				{#if preview.new_players.length}
					<div class="names">
						{#each preview.new_players as name (name)}
							<span class="badge badge-soft badge-sm">{name}</span>
						{/each}
					</div>
				{:else}
					<p class="hint">{t('import.newPlayersNone')}</p>
				{/if}
			</div>
		</section>

		{#each preview.matchdays as day, index (index)}
			<section class="card flex flex-col gap-3 bg-base-100 p-5">
				<header class="dhead">
					<h3 class="font-semibold">{day.date ? formatMatchdayDate(day.date) : '—'}</h3>
					<div class="flex flex-wrap gap-2">
						{#if day.venue}
							<span class="badge badge-soft badge-sm"><Icon name="venue" />{day.venue}</span>
						{/if}
						{#if day.mvp}
							<span class="badge badge-soft badge-sm"><Icon name="star" />{day.mvp}</span>
						{/if}
						{#if day.already_exists}
							<span class="badge badge-soft badge-warning badge-sm">
								{replaceExisting ? t('import.willReplace') : t('import.alreadyExists')}
							</span>
						{/if}
					</div>
				</header>

				{#if day.standings.length}
					<div class="scroll">
						<table class="table table-sm">
							<thead>
								<tr>
									<th>{t('standings.team')}</th>
									<th class="num">{t('standings.played')}</th>
									<th class="num">{t('standings.wins')}</th>
									<th class="num">{t('standings.draws')}</th>
									<th class="num">{t('standings.losses')}</th>
									<th class="num">{t('standings.goalDiff')}</th>
									<th class="num">{t('standings.points')}</th>
									<th class="num">{t('standings.winRate')}</th>
								</tr>
							</thead>
							<tbody>
								{#each day.standings as row (row.name)}
									<tr>
										<td class="font-semibold">{row.name}</td>
										<td class="num">{row.played}</td>
										<td class="num">{row.wins}</td>
										<td class="num">{row.draws}</td>
										<td class="num">{row.losses}</td>
										<td class="num">{row.goal_diff > 0 ? `+${row.goal_diff}` : row.goal_diff}</td>
										<td class="num font-semibold">{row.points}</td>
										<td class="num rate">{formatRate(row.win_rate)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}

				<div class="lineups">
					{#each day.teams as team (team.name)}
						<div class="lineup">
							<span class="lteam">{team.name}</span>
							<span class="lnames">{team.players.join(' · ')}</span>
						</div>
					{/each}
				</div>

				<div class="pmatches">
					{#each day.matches as match, mIndex (mIndex)}
						<div class="pmatch">
							<span class="pside">{match.home_team}</span>
							<span class="pscore">{match.home_score}<i>x</i>{match.away_score}</span>
							<span class="pside away">{match.away_team}</span>
							{#if match.goals.length}
								<span class="pgoals">
									{#each match.goals as goal, gIndex (gIndex)}
										<span class:own={goal.own_goal}>
											{goal.player}{#if goal.own_goal}<i>
													({t('day.ownGoalShort')})</i
												>{:else if goal.assist}<i> &larr; {goal.assist}</i>{/if}
										</span>
									{/each}
								</span>
							{/if}
						</div>
					{/each}
				</div>
			</section>
		{/each}

		<section class="card flex flex-col gap-3 bg-base-100 p-5">
			{#if existingCount > 0}
				<label class="check">
					<input type="checkbox" class="checkbox checkbox-sm" bind:checked={replaceExisting} />
					<span>
						{t('import.replaceExisting')}
						<span class="hint block">{t('import.replaceHint')}</span>
					</span>
				</label>
			{/if}
			<button class="btn btn-primary" disabled={!canCommit || committing} onclick={commit}>
				{committing ? t('import.committing') : t('import.commit')}
			</button>
		</section>
	{/if}

	<section class="card flex flex-col gap-3 bg-base-100 p-5">
		<div class="sec-head">
			<h3 class="font-semibold">{t('import.formatTitle')}</h3>
			<button class="btn btn-ghost btn-sm" onclick={copyTemplate}>
				{t('import.copyTemplate')}
			</button>
		</div>
		<p class="hint">{t('import.formatIntro')}</p>
		<ul class="rules">
			<li>{t('import.ruleHeader')}</li>
			<li>{t('import.ruleTeam')}</li>
			<li>{t('import.ruleMatch')}</li>
			<li>{t('import.ruleGoalsInline')}</li>
			<li>{t('import.ruleAssist')}</li>
			<li>{t('import.ruleOwnGoal2')}</li>
			<li>{t('import.ruleMultiplier')}</li>
			<li>{t('import.ruleMvp')}</li>
			<li>{t('import.ruleSeparator')}</li>
			<li>{t('import.ruleComment')}</li>
		</ul>
		<pre class="template">{TEMPLATE}</pre>
	</section>
</div>

<style>
	.import {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.block {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.blabel {
		font-size: 0.72rem;
		font-weight: 600;
		color: color-mix(in oklch, var(--color-base-content) 82%, transparent);
	}
	.notes {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 0.84rem;
		line-height: 1.55;
		white-space: pre;
		overflow-wrap: normal;
		overflow-x: auto;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.hint {
		font-size: 0.76rem;
		color: var(--ink-muted);
	}
	.sum {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.issues {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.issue {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		padding: 8px 10px;
		border-radius: var(--radius-field);
		background: color-mix(in oklch, var(--color-warning) 12%, transparent);
		color: var(--ink-warning);
		font-size: 0.8rem;
		line-height: 1.45;
	}
	.issue.err {
		background: color-mix(in oklch, var(--color-error) 12%, transparent);
		color: color-mix(in oklab, var(--color-error) 90%, var(--color-base-content));
	}
	.imsg code {
		display: inline-block;
		margin-left: 6px;
		padding: 1px 5px;
		border-radius: 4px;
		background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 0.74rem;
	}
	.names {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.dhead {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}
	.scroll {
		overflow-x: auto;
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.rate {
		font-weight: 600;
		color: var(--ink-primary);
	}
	.lineups {
		display: flex;
		flex-direction: column;
		gap: 5px;
		font-size: 0.78rem;
	}
	.lineup {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 8px;
	}
	.lteam {
		font-weight: 700;
		min-width: 5.5rem;
	}
	.lnames {
		color: var(--ink-muted);
	}
	.pmatches {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}
	.pmatch {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		align-items: center;
		gap: 8px;
		padding: 6px 10px;
		border-radius: var(--radius-field);
		background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
		font-size: 0.82rem;
	}
	.pside {
		text-align: right;
		overflow-wrap: anywhere;
	}
	.pside.away {
		text-align: left;
	}
	.pscore {
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.pscore i {
		margin: 0 3px;
		font-style: normal;
		opacity: 0.4;
		font-weight: 400;
	}
	.pgoals {
		grid-column: 1 / -1;
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 4px 10px;
		font-size: 0.72rem;
		color: var(--ink-muted);
	}
	.pgoals .own {
		color: var(--ink-warning);
	}
	.pgoals i {
		font-style: normal;
	}
	.check {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		font-size: 0.86rem;
		cursor: pointer;
	}
	.sec-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}
	.rules {
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-size: 0.8rem;
		color: color-mix(in oklch, var(--color-base-content) 82%, transparent);
		list-style: disc;
		padding-left: 18px;
	}
	.template {
		padding: 12px 14px;
		border-radius: var(--radius-field);
		background: color-mix(in oklch, var(--color-base-content) 6%, transparent);
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 0.76rem;
		line-height: 1.5;
		overflow-x: auto;
	}
</style>
