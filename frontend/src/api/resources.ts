import client from './client';
import type {
  Alert,
  Camera,
  DashboardStats,
  DetectionEvent,
  PaginatedQuery,
  Roi,
  RoiCreatePayload,
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
  const response = await client.post<Scene>(`/scenes/${sceneId}/baseline`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function listRois(sceneId: number): Promise<Roi[]> {
  const response = await client.get<Roi[]>('/rois', { params: { scene_id: sceneId } });
  return response.data;
}

export async function createRoi(sceneId: number, data: RoiCreatePayload): Promise<Roi> {
  const response = await client.post<Roi>('/rois', { ...data, scene_id: sceneId });
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
