import client from './client';
import type {
  Alert,
  PaginatedQuery,
  Roi,
  RoiCreatePayload,
  Rule,
  RuleCreatePayload,
  RuleUpdatePayload,
  Scene,
  User,
  WorkOrder,
} from './types';

export async function listAlerts(params: PaginatedQuery = {}): Promise<Alert[]> {
  const response = await client.get<Alert[]>('/alerts', { params });
  return response.data;
}

export async function listWorkOrders(params: PaginatedQuery = {}): Promise<WorkOrder[]> {
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
