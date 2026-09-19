import { writable } from 'svelte/store';

export type PageId = 'dashboard' | 'workshops' | 'mills' | 'samples' | 'passes' | 'rework';

export const page = writable<PageId>('dashboard');

/** 从回磨任务跳转取样页时预选的研磨机 id(消费后清空) */
export const samplePrefillMillId = writable<number | null>(null);
