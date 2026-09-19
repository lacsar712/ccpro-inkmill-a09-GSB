import type { MillStatus, ReworkTicketStatus } from './types';

export const millStatusLabel: Record<MillStatus, string> = {
  grinding: '研磨中',
  idle: '待机',
  wash: '清洗',
};

export const reworkStatusLabel: Record<ReworkTicketStatus, string> = {
  open: '待回磨',
  rework_done: '回磨完成',
  closed: '已关闭',
};
