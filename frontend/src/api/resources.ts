import client from './client';
import type {
  AlertTrendPoint,
  Alert,
  BatchAlertAction,
  BatchAlertResponse,
  Camera,
  DashboardStats,
  DetectionEvent,
  NotificationChannel,
  NotificationChannelCreatePayload,
  NotificationChannelUpdatePayload,
  NotificationGroup,
  NotificationGroupCreatePayload,
  NotificationGroupUpdatePayload,
  PaginatedQuery,
  Roi,
  RoiCreatePayload,
  RoiUpdatePayload,
  Rule,
  RuleCreatePayload,
  RuleUpdatePayload,
  Scene,
  SceneCreatePayload,
  User,
  UserCreatePayload,
  UserUpdatePayload,
  WorkOrder,
} from './types';

export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await client.get<DashboardStats>('/dashboard/stats');
  return response.data;
}

export async function getAlertTrend(days: number = 7): Promise<AlertTrendPoint[]> {
  const response = await client.get<AlertTrendPoint[]>('/dashboard/alert-trend', { params: { days } });
  return response.data;
}

export async function listAlerts(params: PaginatedQuery = {}): Promise<Alert[]> {
  const response = await client.get<Alert[]>('/alerts', { params });
  return response.data;
}

export async function listWorkOrders(params: PaginatedQuery & { alert_id?: number } = {}): Promise<WorkOrder[]> {
  const response = await client.get<WorkOrder[]>('/work-orders', { params });
  return response.data;
}

export async function listScenes(cameraId?: number): Promise<Scene[]>;
export async function listScenes(params?: PaginatedQuery): Promise<Scene[]>;
export async function listScenes(cameraIdOrParams: number | PaginatedQuery = {}): Promise<Scene[]> {
  const params = typeof cameraIdOrParams === 'number' ? { camera_id: cameraIdOrParams } : cameraIdOrParams;
  const response = await client.get<Scene[]>('/scenes', { params });
  return response.data;
}

export async function getScene(sceneId: number): Promise<Scene> {
  const response = await client.get<Scene>(`/scenes/${sceneId}`);
  return response.data;
}

export async function createScene(data: SceneCreatePayload): Promise<Scene> {
  const response = await client.post<Scene>('/scenes', data);
  return response.data;
}

export async function updateSceneBaseline(sceneId: number, file: File): Promise<Scene> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await client.put<Scene>(`/scenes/${sceneId}/baseline`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function listRois(sceneId: number): Promise<Roi[]> {
  const response = await client.get<Roi[]>('/rois', { params: { scene_id: sceneId } });
  return response.data;
}

export async function createRoi(sceneId: number, data: RoiCreatePayload): Promise<Roi> {
  const payload = { ...data, scene_id: sceneId, zone_type: 'polygon' as const, normalized_coords: true };
  const response = await client.post<Roi>('/rois', payload);
  return response.data;
}

export async function updateRoi(roiId: number, data: RoiUpdatePayload): Promise<Roi> {
  const response = await client.put<Roi>(`/rois/${roiId}`, data);
  return response.data;
}

export async function deleteRoi(roiId: number): Promise<void> {
  await client.delete(`/rois/${roiId}`);
}

export async function listRules(cameraId: number): Promise<Rule[]> {
  const response = await client.get<Rule[]>('/rules', { params: { camera_id: cameraId } });
  return response.data;
}

export async function createRule(data: RuleCreatePayload): Promise<Rule> {
  const response = await client.post<Rule>('/rules', data);
  return response.data;
}

export async function updateRule(ruleId: number, data: RuleUpdatePayload): Promise<Rule> {
  const response = await client.put<Rule>(`/rules/${ruleId}`, data);
  return response.data;
}

export async function deleteRule(ruleId: number): Promise<void> {
  await client.delete(`/rules/${ruleId}`);
}

export async function triggerSnapshot(cameraId: number): Promise<Scene> {
  const response = await client.post<Scene>(`/cameras/${cameraId}/snapshot`);
  return response.data;
}

export async function listUsers(params: PaginatedQuery = {}): Promise<User[]> {
  const response = await client.get<User[]>('/users', { params });
  return response.data;
}

export async function getUser(id: number): Promise<User> {
  const response = await client.get<User>(`/users/${id}`);
  return response.data;
}

export async function createUser(data: UserCreatePayload): Promise<User> {
  const response = await client.post<User>('/users', data);
  return response.data;
}

export async function updateUser(id: number, data: UserUpdatePayload): Promise<User> {
  const response = await client.put<User>(`/users/${id}`, data);
  return response.data;
}

export async function deleteUser(id: number): Promise<void> {
  await client.delete(`/users/${id}`);
}

export async function confirmAlert(id: number): Promise<Alert> {
  const { data } = await client.post<Alert>(`/alerts/${id}/confirm`);
  return data;
}

export async function markAlertFalsePositive(id: number, reason?: string): Promise<Alert> {
  const { data } = await client.post<Alert>(`/alerts/${id}/false-positive`, { reason });
  return data;
}

export async function resolveAlert(id: number, notes?: string): Promise<Alert> {
  const { data } = await client.post<Alert>(`/alerts/${id}/resolve`, { notes });
  return data;
}

export async function transitionWorkOrder(id: number, body: { target: string; notes?: string }): Promise<WorkOrder> {
  const { data } = await client.post<WorkOrder>(`/work-orders/${id}/transition`, body);
  return data;
}

export async function assignWorkOrder(id: number, body: { user_id: number }): Promise<WorkOrder> {
  const { data } = await client.post<WorkOrder>(`/work-orders/${id}/assign`, body);
  return data;
}

export async function getAlert(id: number): Promise<Alert> {
  const { data } = await client.get<Alert>(`/alerts/${id}`);
  return data;
}

export async function listCameras(params: PaginatedQuery = {}): Promise<Camera[]> {
  const response = await client.get<Camera[]>('/cameras', { params });
  return response.data;
}

export async function getCamera(id: number): Promise<Camera> {
  const { data } = await client.get<Camera>(`/cameras/${id}`);
  return data;
}

export async function listDetectionEvents(params?: PaginatedQuery & {
  camera_id?: number;
  roi_id?: number;
  detected_after?: string;
  detected_before?: string;
}): Promise<DetectionEvent[]> {
  const { data } = await client.get<DetectionEvent[]>('/detection-events', { params });
  return data;
}

export async function exportDetectionEvents(params: { camera_id?: number; roi_id?: number } = {}): Promise<Blob> {
  const response = await client.get('/detection-events/export', { params, responseType: 'blob' });
  return response.data;
}

export async function exportAlerts(params: { severity?: string; status?: string } = {}): Promise<Blob> {
  const response = await client.get('/alerts/export', { params, responseType: 'blob' });
  return response.data;
}

export async function batchAlerts(alertIds: number[], action: BatchAlertAction): Promise<BatchAlertResponse> {
  const { data } = await client.post<BatchAlertResponse>('/alerts/batch', { alert_ids: alertIds, action });
  return data;
}

export async function listNotificationGroups(params?: PaginatedQuery): Promise<NotificationGroup[]> {
  const { data } = await client.get<NotificationGroup[]>('/notification-groups', { params });
  return data;
}

export async function getNotificationGroup(id: number): Promise<NotificationGroup> {
  const { data } = await client.get<NotificationGroup>(`/notification-groups/${id}`);
  return data;
}

export async function createNotificationGroup(payload: NotificationGroupCreatePayload): Promise<NotificationGroup> {
  const { data } = await client.post<NotificationGroup>('/notification-groups', payload);
  return data;
}

export async function updateNotificationGroup(id: number, payload: NotificationGroupUpdatePayload): Promise<NotificationGroup> {
  const { data } = await client.put<NotificationGroup>(`/notification-groups/${id}`, payload);
  return data;
}

export async function deleteNotificationGroup(id: number): Promise<void> {
  await client.delete(`/notification-groups/${id}`);
}

export async function createNotificationChannel(groupId: number, payload: NotificationChannelCreatePayload): Promise<NotificationChannel> {
  const { data } = await client.post<NotificationChannel>(`/notification-groups/${groupId}/channels`, payload);
  return data;
}

export async function updateNotificationChannel(id: number, payload: NotificationChannelUpdatePayload): Promise<NotificationChannel> {
  const { data } = await client.put<NotificationChannel>(`/notification-groups/channels/${id}`, payload);
  return data;
}

export async function deleteNotificationChannel(id: number): Promise<void> {
  await client.delete(`/notification-groups/channels/${id}`);
}

export async function testNotificationChannel(id: number): Promise<{ channel_id: number; success: boolean }> {
  const { data } = await client.post<{ channel_id: number; success: boolean }>(`/notification-groups/channels/${id}/test`);
  return data;
}
