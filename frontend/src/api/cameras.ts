import client from './client';
import type { Camera, CameraCreatePayload, CameraUpdatePayload, PaginatedQuery } from './types';

export async function listCameras(params: PaginatedQuery = {}): Promise<Camera[]> {
  const response = await client.get<Camera[]>('/cameras', { params });
  return response.data;
}

export async function getCamera(id: number): Promise<Camera> {
  const response = await client.get<Camera>(`/cameras/${id}`);
  return response.data;
}

export async function createCamera(payload: CameraCreatePayload): Promise<Camera> {
  const response = await client.post<Camera>('/cameras', payload);
  return response.data;
}

export async function updateCamera(id: number, payload: CameraUpdatePayload): Promise<Camera> {
  const response = await client.put<Camera>(`/cameras/${id}`, payload);
  return response.data;
}

export async function deleteCamera(id: number): Promise<void> {
  await client.delete(`/cameras/${id}`);
}
