<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import { page, samplePrefillMillId } from '../lib/nav';
  import { reworkStatusLabel } from '../lib/labels';
  import type { Mill, ReworkTicket, ReworkTicketStatus } from '../lib/types';

  let rows: ReworkTicket[] = [];
  let mills: Mill[] = [];
  let error = '';
  let detailError = '';
  let selectedId: number | null = null;

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

  let editForm = {
    millId: '',
    complaintRef: '',
    severityPaS: '',
    openedAt: '',
  };

  $: selected = rows.find((r) => r.id === selectedId) || null;

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

  function syncEditForm(row: ReworkTicket) {
    editForm = {
      millId: String(row.millId),
      complaintRef: row.complaintRef,
      severityPaS: String(row.severityPaS),
      openedAt: toLocalInput(row.openedAt),
    };
  }

  function select(row: ReworkTicket) {
    selectedId = row.id;
    detailError = '';
    syncEditForm(row);
  }

  async function create() {
    error = '';
    try {
      const created = await api<ReworkTicket>('/rework-tickets', {
        method: 'POST',
        body: JSON.stringify({
          millId: Number(form.millId),
          complaintRef: form.complaintRef,
          severityPaS: Number(form.severityPaS),
          openedAt: form.openedAt,
        }),
      });
      form = {
        millId: form.millId,
        complaintRef: '',
        severityPaS: '1.0',
        openedAt: nowLocal(),
      };
      await load();
      select(created);
    } catch (e) {
      error = e instanceof Error ? e.message : '创建失败';
    }
  }

  async function saveEdit() {
    if (!selected) return;
    detailError = '';
    try {
      await api(`/rework-tickets/${selected.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          millId: Number(editForm.millId),
          complaintRef: editForm.complaintRef,
          severityPaS: Number(editForm.severityPaS),
          openedAt: editForm.openedAt,
        }),
      });
      await load();
    } catch (e) {
      detailError = e instanceof Error ? e.message : '保存失败';
    }
  }

  async function transition(target: ReworkTicketStatus) {
    if (!selected) return;
    detailError = '';
    try {
      await api(`/rework-tickets/${selected.id}/transition`, {
        method: 'POST',
        body: JSON.stringify({ status: target }),
      });
      await load();
    } catch (e) {
      detailError = e instanceof Error ? e.message : '流转失败';
    }
  }

  function gotoSamples() {
    if (!selected) return;
    samplePrefillMillId.set(selected.millId);
    page.set('samples');
  }
</script>

<header class="page-head">
  <h1>客诉回磨任务</h1>
  <p>客诉触发的回磨流转:待回磨 → 回磨完成 → 已关闭;关闭前需有登记后的粘度取样</p>
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
    <div class="field"><label>客诉编号<input bind:value={form.complaintRef} placeholder="如 客诉 C-2026-042" /></label></div>
    <div class="field"><label>粘度目标 Pa·s<input type="number" step="0.0001" min="0.0001" bind:value={form.severityPaS} /></label></div>
    <div class="field"><label>登记时间<input type="datetime-local" bind:value={form.openedAt} /></label></div>
  </div>
  <div class="actions">
    <button class="btn-primary" on:click={create}>创建</button>
  </div>
</section>

{#if selected}
  <section class="panel">
    <h2>任务详情 #{selected.id}</h2>
    <p>
      <span class="badge {selected.status}">{reworkStatusLabel[selected.status]}</span>
      <span class="muted">登记 {selected.openedAt}</span>
      {#if selected.closedAt}
        <span class="muted">· 关闭 {selected.closedAt}</span>
      {/if}
    </p>
    {#if detailError}
      <div class="err">{detailError}</div>
    {/if}
    <div class="fields">
      <div class="field">
        <label>研磨机
          <select bind:value={editForm.millId} disabled={selected.status === 'closed'}>
            {#each mills as m}
              <option value={String(m.id)}>{m.millCode}</option>
            {/each}
          </select>
        </label>
      </div>
      <div class="field"><label>客诉编号<input bind:value={editForm.complaintRef} disabled={selected.status === 'closed'} /></label></div>
      <div class="field"><label>粘度目标 Pa·s<input type="number" step="0.0001" min="0.0001" bind:value={editForm.severityPaS} disabled={selected.status === 'closed'} /></label></div>
      <div class="field"><label>登记时间<input type="datetime-local" bind:value={editForm.openedAt} disabled={selected.status === 'closed'} /></label></div>
    </div>
    {#if selected.status === 'closed'}
      <p class="muted">工单已关闭,粘度目标已锁定,不可再修改。</p>
    {/if}
    <div class="actions">
      {#if selected.status === 'open'}
        <button class="btn-primary" on:click={() => transition('rework_done')}>标记回磨完成</button>
      {:else if selected.status === 'rework_done'}
        <button class="btn-primary" on:click={() => transition('closed')}>关闭工单</button>
      {/if}
      {#if selected.status !== 'closed'}
        <button class="btn-ghost" on:click={saveEdit}>保存修改</button>
      {/if}
      <button class="btn-ghost" on:click={gotoSamples}>前往粘度取样</button>
      <button class="btn-ghost" on:click={() => (selectedId = null)}>收起</button>
    </div>
  </section>
{/if}

<section class="panel">
  <table class="data-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>研磨机</th>
        <th>客诉编号</th>
        <th>粘度目标 Pa·s</th>
        <th>状态</th>
        <th>登记时间</th>
        <th>关闭时间</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{millLabel(row.millId)}</td>
          <td>{row.complaintRef}</td>
          <td>{row.severityPaS}</td>
          <td><span class="badge {row.status}">{reworkStatusLabel[row.status]}</span></td>
          <td>{row.openedAt}</td>
          <td>{row.closedAt || '—'}</td>
          <td class="ops">
            <button class="link-btn" on:click={() => select(row)}>详情</button>
          </td>
        </tr>
      {:else}
        <tr><td colspan="8">暂无数据</td></tr>
      {/each}
    </tbody>
  </table>
</section>
