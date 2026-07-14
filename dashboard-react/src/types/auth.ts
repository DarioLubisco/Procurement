// Strict TypeScript types for the auth system

export interface Permission {
  r: boolean;
  w: boolean;
}

export type ModuleName = 'chat' | 'caja' | 'cxp' | 'admin';

export interface UserPermissions {
  [module: string]: Permission;
}

export interface AuthUser {
  id: number;
  username: string;
  nombre: string;
  email?: string;
  permissions: UserPermissions;
}

export interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}
