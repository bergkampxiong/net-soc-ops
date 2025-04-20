import request from '../utils/request';

export interface Credential {
  id: number;
  name: string;
  type: string;
  username: string;
  password: string;
  enable_password?: string;
  private_key?: string;
  created_at: string;
  updated_at: string;
}

export interface CredentialCreate {
  name: string;
  type: string;
  username: string;
  password: string;
  enable_password?: string;
  private_key?: string;
}

export interface CredentialUpdate {
  name?: string;
  type?: string;
  username?: string;
  password?: string;
  enable_password?: string;
  private_key?: string;
}

export const getCredentials = async (): Promise<Credential[]> => {
  try {
    console.log('Fetching credentials...');
    const response = await request.get<Credential[]>('/device/credentials');
    console.log('Credentials response:', response);
    return response.data;
  } catch (error) {
    console.error('Error fetching credentials:', error);
    throw error;
  }
};

export const getCredential = async (id: number): Promise<Credential> => {
  const response = await request.get<Credential>(`/device/credentials/${id}`);
  return response.data;
};

export const createCredential = async (data: CredentialCreate): Promise<Credential> => {
  const response = await request.post<Credential>('/device/credentials', data);
  return response.data;
};

export const updateCredential = async (id: number, data: CredentialUpdate): Promise<Credential> => {
  const response = await request.put<Credential>(`/device/credentials/${id}`, data);
  return response.data;
};

export const deleteCredential = async (id: number): Promise<void> => {
  await request.delete(`/device/credentials/${id}`);
}; 