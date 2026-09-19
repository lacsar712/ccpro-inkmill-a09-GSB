import { writable } from 'svelte/store';

export type PageId = 'dashboard' | 'workshops' | 'mills' | 'samples' | 'passes' | 'tickets';

export const page = writable<PageId>('dashboard');

/** 从回磨任务跳转粘度取样页时预选研磨机 */
export const sampleMillPrefill = writable<number | null>(null);
