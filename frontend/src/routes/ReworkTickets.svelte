<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import { page, sampleMillPrefill } from '../lib/nav';
  import { reworkStatusLabel } from '../lib/labels';
  import type { Mill, ReworkTicket, ReworkTicketStatus } from '../lib/types';

  let rows: ReworkTicket[] = [];
  let mills: Mill[] = [];
  let error = '';

  function nowLocal(): string {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  }

  let form = {
    millId: '',
    complaintRef: '',
    severityPaS: '1.0',
    openedAt: nowLocal(),
  };

  let detail: ReworkTicket | null = null;
  let editForm = { millId: '', complaintRef: '', severityPaS: '', openedAt: '' };

  async function load() {
    error = '';
    try {
      [rows, mills] = await Promise.all([
        api<ReworkTicket[]>('/rework-tickets'),
        api<Mill[]>('/mills'),
      ]);
      if (!form.millId && mills[0]) form.millId = String(mills[0].id);
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    }
  }

  onMount(load);

  function millLabel(id: number): string {
    const m = mills.find((x) => x.id === id);
    return m ? `${m.millCode} (#${m.id})` : `#${id}`;
  }

  function toLocalInput(iso: string): string {
    const d = new Date(iso.replace(' ', 'T'));
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  }

  async function create() {
    error = '';
    try {
      await api('/rework-tickets', {
        method: 'POST',
        body: JSON.stringify({
          millId: Number(form.millId),
          complaintRef: form.complaintRef,
          severityPaS: Number(form.severityPaS),
          openedAt: form.openedAt,
        }),
      });
      form = {
        millId: mills[0] ? String(mills[0].id) : '',
        complaintRef: '',
        severityPaS: '1.0',
        openedAt: nowLocal(),
      };
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '创建失败';
    }
  }

  async function openDetail(id: number) {
    error = '';
    try {
      detail = await api<ReworkTicket>(`/rework-tickets/${id}`);
      editForm = {
        millId: String(detail.millId),
        complaintRef: detail.complaintRef,
        severityPaS: String(detail.severityPaS),
        openedAt: toLocalInput(detail.openedAt),
      };
    } catch (e) {
      error = e instanceof Error ? e.message : '加载详情失败';
    }
  }

  function closeDetail() {
    detail = null;
  }

  async function saveEdit() {
    if (!detail) return;
    error = '';
    try {
      await api(`/rework-tickets/${detail.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          millId: Number(editForm.millId),
          complaintRef: editForm.complaintRef,
          severityPaS: Number(editForm.severityPaS),
          openedAt: editForm.openedAt,
        }),
      });
      await load();
      await openDetail(detail.id);
    } catch (e) {
      error = e instanceof Error ? e.message : '保存失败';
    }
  }

  async function transition(to: ReworkTicketStatus) {
    if (!detail) return;
    error = '';
    try {
      await api(`/rework-tickets/${detail.id}/status`, {
        method: 'POST',
        body: JSON.stringify({ status: to }),
      });
      await load();
      await openDetail(detail.id);
    } catch (e) {
      error = e instanceof Error ? e.message : '状态流转失败';
    }
  }

  function gotoSamples() {
    if (!detail) return;
    sampleMillPrefill.set(detail.millId);
    page.set('samples');
  }

  const steps: ReworkTicketStatus[] = ['open', 'rework_done', 'closed'];
</script>

<header class="page-head">
  <h1>回磨任务</h1>
  <p>客诉回磨:登记客诉单号与粘度偏差,回磨完成后凭开立后的粘度取样关闭</p>
</header>

{#if error}
  <div class="err">{error}</div>
{/if}

<section class="panel">
  <h2>新建回磨任务</h2>
  <div class="fields">
    <div class="field">
      <label>研磨机
        <select bind:value={form.millId}>
          {#each mills as m}
            <option value={String(m.id)}>{m.millCode}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field"><label>客诉单号<input bind:value={form.complaintRef} placeholder="如 KS-2026-0918" /></label></div>
    <div class="field"><label>粘度偏差 Pa·s<input type="number" step="0.0001" min="0.0001" bind:value={form.severityPaS} /></label></div>
    <div class="field"><label>开立时间<input type="datetime-local" bind:value={form.openedAt} /></label></div>
  </div>
  <div class="actions">
    <button class="btn-primary" on:click={create}>创建</button>
  </div>
</section>

{#if detail}
  <section class="panel">
    <h2>任务详情 #{detail.id} · {detail.complaintRef}</h2>

    <div class="flow">
      {#each steps as s, i}
        <span class="step" class:current={detail.status === s} class:done={steps.indexOf(detail.status) > i}>
          {reworkStatusLabel[s]}
        </span>
        {#if i < steps.length - 1}<span class="arrow">→</span>{/if}
      {/each}
    </div>

    {#if detail.status === 'closed'}
      <p class="muted">已于 {detail.closedAt} 关闭,粘度目标等字段不可再修改。</p>
    {:else}
      <div class="fields">
        <div class="field">
          <label>研磨机
            <select bind:value={editForm.millId}>
              {#each mills as m}
                <option value={String(m.id)}>{m.millCode}</option>
              {/each}
            </select>
          </label>
        </div>
        <div class="field"><label>客诉单号<input bind:value={editForm.complaintRef} /></label></div>
        <div class="field"><label>粘度偏差 Pa·s<input type="number" step="0.0001" min="0.0001" bind:value={editForm.severityPaS} /></label></div>
        <div class="field"><label>开立时间<input type="datetime-local" bind:value={editForm.openedAt} /></label></div>
      </div>
      <div class="actions">
        <button class="btn-ghost" on:click={saveEdit}>保存修改</button>
      </div>
    {/if}

    <div class="actions">
      {#if detail.status === 'open'}
        <button class="btn-primary" on:click={() => transition('rework_done')}>标记回磨完成</button>
      {:else if detail.status === 'rework_done'}
        <button
          class="btn-primary"
          disabled={(detail.samplesAfterOpen ?? 0) < 1}
          title={(detail.samplesAfterOpen ?? 0) < 1 ? '关闭前要求该机在开立时间之后至少有 1 条粘度取样' : ''}
          on:click={() => transition('closed')}>复检通过,关闭任务</button>
        <span class="muted">
          开立后取样 {detail.samplesAfterOpen ?? 0} 条
          {#if (detail.samplesAfterOpen ?? 0) < 1}(需至少 1 条才能关闭){/if}
        </span>
      {/if}
      {#if detail.status !== 'closed'}
        <button class="btn-ghost" on:click={gotoSamples}>前往粘度取样</button>
      {/if}
      <button class="btn-ghost" on:click={closeDetail}>收起</button>
    </div>
  </section>
{/if}

<section class="panel">
  <table class="data-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>客诉单号</th>
        <th>研磨机</th>
        <th>偏差 Pa·s</th>
        <th>状态</th>
        <th>开立时间</th>
        <th>关闭时间</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{row.complaintRef}</td>
          <td>{millLabel(row.millId)}</td>
          <td>{row.severityPaS}</td>
          <td><span class="badge {row.status}">{reworkStatusLabel[row.status]}</span></td>
          <td>{row.openedAt}</td>
          <td>{row.closedAt ?? '—'}</td>
          <td class="ops">
            <button class="link-btn" on:click={() => openDetail(row.id)}>详情</button>
          </td>
        </tr>
      {:else}
        <tr><td colspan="8">暂无数据</td></tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  .flow {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.9rem;
    font-size: 0.85rem;
  }

  .step {
    padding: 0.25rem 0.6rem;
    border: 1px solid var(--line);
    color: var(--steel);
    border-radius: 2px;
  }

  .step.done {
    color: var(--ok);
    border-color: rgba(61, 154, 106, 0.5);
  }

  .step.current {
    color: var(--vermillion-400);
    border-color: var(--vermillion-700);
  }

  .arrow {
    color: var(--steel);
  }

  .actions {
    align-items: center;
  }

  .btn-primary:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
</style>
