export type CameraStatus = 'active' | 'inactive' | 'maintenance';
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertStatus = 'pending' | 'confirmed' | 'false_positive' | 'resolved';
export type AlertEventType = 'created' | 'confirmed' | 'resolved' | 'false_positive' | 'escalated';
export type RuleType = 'obstruction_duration' | 'obstruction_area' | 'litter' | 'fire_smoke';
export type WorkOrderStatus = 'open' | 'in_progress' | 'closed' | 'cancelled';
export type UserRole = 'admin' | 'operator' | 'viewer';
export type NotificationChannelType = 'wecom' | 'sms' | 'email';

export interface PaginatedQuery {
  skip?: number;
  limit?: number;
}

export interface Camera {
  id: number;
  name: string;
  location: string;
  ip: string;
  port: number;
  username?: string;
  status: CameraStatus;
  created_at: string;
  updated_at: string;
}

export interface CameraCreatePayload {
  name: string;
  location: string;
  ip: string;
  port: number;
  username: string;
  password: string;
  status: CameraStatus;
}

export interface CameraUpdatePayload {
  name?: string;
  location?: string;
  ip?: string;
  port?: number;
  username?: string;
  password?: string;
  status?: CameraStatus;
}

export interface Alert {
  id: number;
  camera_id: number;
  roi_id: number | null;
  rule_id: number | null;
  alert_type: RuleType;
  severity: AlertSeverity;
  status: AlertStatus;
  evidence_image_path: string | null;
  detected_at: string;
  resolved_at: string | null;
  event_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WorkOrder {
  id: number;
  alert_id: number;
  assigned_to: number | null;
  status: WorkOrderStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Scene {
  id: number;
  camera_id: number;
  name: string;
  baseline_image_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface SceneCreatePayload {
  camera_id: number;
  name: string;
}

export type ZoneType = 'polygon' | 'rect';

export type RoiGeometry = {
  type: 'polygon';
  points: Array<[number, number]>;
};

export interface Roi {
  id: number;
  scene_id: number;
  name: string;
  zone_type: ZoneType;
  geometry: RoiGeometry;
  normalized_coords: boolean;
  color: string | null;
  created_at: string;
  updated_at: string;
}

export interface RoiCreatePayload {
  name: string;
  geometry: RoiGeometry;
}

export interface RoiUpdatePayload {
  name?: string;
  geometry?: RoiGeometry;
}

export interface RuleThresholdConfig {
  threshold?: number;
  min_area?: number;
  max_count?: number;
  duration_seconds?: number;
}

export interface Rule {
  id: number;
  camera_id: number;
  roi_id: number | null;
  rule_type: RuleType;
  threshold_config: RuleThresholdConfig;
  priority: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface RuleCreatePayload {
  camera_id: number;
  roi_id: number | null;
  rule_type: RuleType;
  threshold_config: RuleThresholdConfig;
  priority: number;
  enabled: boolean;
}

export type RuleUpdatePayload = Partial<Omit<RuleCreatePayload, 'camera_id'>>;

export interface UserCreatePayload {
  username: string;
  display_name: string;
  password: string;
  role?: UserRole;
  enabled?: boolean;
}

export interface UserUpdatePayload {
  username?: string;
  display_name?: string;
  password?: string;
  role?: UserRole;
  enabled?: boolean;
}

export interface User {
  id: number;
  username: string;
  display_name: string;
  role: UserRole;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  cameras_total: number;
  cameras_active: number;
  cameras_inactive: number;
  cameras_error: number;
  scenes_total: number;
  alerts_total: number;
  alerts_pending: number;
  alerts_confirmed: number;
  alerts_false_positive: number;
  alerts_resolved: number;
  alerts_by_severity: Record<string, number>;
  work_orders_total: number;
  work_orders_open: number;
  work_orders_in_progress: number;
  work_orders_closed: number;
}

export type DetectorType = 'image_compare' | 'yolo' | 'blue_box';

export interface DetectionEvent {
  id: number;
  camera_id: number;
  roi_id: number | null;
  detector_type: DetectorType;
  confidence: number | null;
  evidence_path: string | null;
  event_metadata: Record<string, unknown>;
  detected_at: string;
}

export interface AlertEvent {
  event_type: AlertEventType;
  alert_id: number;
  camera_id: number;
  severity: AlertSeverity;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface NotificationChannel {
  id: number;
  group_id: number;
  channel_type: NotificationChannelType;
  config: Record<string, unknown>;
  enabled: boolean;
}

export interface NotificationGroup {
  id: number;
  name: string;
  channels: { severities: string[] };
  enabled: boolean;
  created_at: string;
  updated_at: string;
  notification_channels: NotificationChannel[];
}

export interface NotificationGroupCreatePayload {
  name: string;
  severities: string[];
  enabled?: boolean;
}

export interface NotificationGroupUpdatePayload {
  name?: string;
  severities?: string[];
  enabled?: boolean;
}

export interface NotificationChannelCreatePayload {
  channel_type: NotificationChannelType;
  config: Record<string, unknown>;
  enabled?: boolean;
}

export interface NotificationChannelUpdatePayload {
  config?: Record<string, unknown>;
  enabled?: boolean;
}

export type BatchAlertAction = 'confirm' | 'false_positive' | 'resolve';

export interface BatchAlertResponse {
  processed: number;
  failed: { id: number; error: string }[];
}

export interface AlertTrendPoint {
  date: string;
  count: number;
}

export interface WorkerStatus {
  status: string;
  last_run_at: string | null;
  total_inspections: number;
  successful: number;
  failed: number;
  cameras_active: number;
  avg_duration_ms: number;
  updated_at: string | null;
  is_stale: boolean;
}
