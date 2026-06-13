import type { AlertSeverity, AlertStatus, CameraStatus, WorkOrderStatus } from '@/api/types';

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
  cancelled: 'danger',
};

const ALERT_SEVERITY_MAP: Record<AlertSeverity, TagType> = {
  critical: 'danger',
  high: 'danger',
  medium: 'warning',
  low: 'success',
};

const ALERT_STATUS_MAP: Record<AlertStatus, TagType> = {
  resolved: 'success',
  confirmed: 'warning',
  pending: 'info',
  false_positive: 'danger',
};

export function cameraStatusTagType(status: CameraStatus): TagType {
  return CAMERA_STATUS_MAP[status] ?? '';
}

export function workOrderStatusTagType(status: WorkOrderStatus): TagType {
  return WORK_ORDER_STATUS_MAP[status] ?? '';
}

export function alertSeverityTagType(severity: AlertSeverity): TagType {
  return ALERT_SEVERITY_MAP[severity] ?? 'info';
}

export function alertStatusTagType(status: AlertStatus): TagType {
  return ALERT_STATUS_MAP[status] ?? 'info';
}
