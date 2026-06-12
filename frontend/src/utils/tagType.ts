import type { CameraStatus, WorkOrderStatus } from '@/api/types';

type TagType = '' | 'success' | 'warning' | 'danger' | 'info';

const CAMERA_STATUS_MAP: Record<CameraStatus, TagType> = {
  active: 'success',
  inactive: 'info',
  maintenance: 'warning',
};

const WORK_ORDER_STATUS_MAP: Record<WorkOrderStatus, TagType> = {
  open: 'warning',
  in_progress: '',
  closed: 'info',
};

export function cameraStatusTagType(status: CameraStatus): TagType {
  return CAMERA_STATUS_MAP[status] ?? '';
}

export function workOrderStatusTagType(status: WorkOrderStatus): TagType {
  return WORK_ORDER_STATUS_MAP[status] ?? '';
}
