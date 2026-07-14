export interface AutomationTask {
  TriggerID: number;
  ActionCommand: string;
  IsActive: boolean;
  LastTriggered?: string;
}

export interface ChatMessage {
  agent: "agente_it" | "agente_equivalencias" | "orquestador" | "portero";
  message: string;
}

export interface ChatResponse {
  reply: string;
  raw?: any;
}

export interface SystemStatus {
  agent: string;
  model: string;
  status: string;
}

export interface EquivalentRecord {
  codigo: string;
  codbarras: string;
  descripcion_original: string;
}

export interface AIAnalysisResult {
  registro: EquivalentRecord;
  atributos: {
    principio_activo: string | null;
    concentracion: string | null;
    forma_farmaceutica: string | null;
  };
}
