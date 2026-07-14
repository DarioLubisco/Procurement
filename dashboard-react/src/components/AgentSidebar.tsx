import { useEffect, useState } from 'react';
import { Bot, Terminal } from 'lucide-react';

export interface AgentInfo {
  id: string;
  name: string;
  model?: string;
  status?: string;
}

interface Props {
  activeAgent: string;
  setActiveAgent: (id: string) => void;
}

const AgentSidebar: React.FC<Props> = ({ activeAgent, setActiveAgent }) => {
  const [agents, setAgents] = useState<AgentInfo[]>([
    { id: 'orquestador', name: 'Orquestador Central', status: 'checking...' },
    { id: 'portero', name: 'Portero Central', status: 'online', model: 'webhook/n8n' },
    { id: 'agente_it', name: 'Sub-Agente IT', status: 'online', model: 'deepseek-v4-flash' },
    { id: 'agente_equivalencias', name: 'Agente Equivalencias', status: 'online', model: 'deepseek-v4-flash' },
  ]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`/api/orquestador/status`);
        if (res.ok) {
          const data = await res.json();
          setAgents(prev =>
            prev.map(a =>
              a.id === 'orquestador' ? { ...a, status: data.status, model: data.model } : a
            )
          );
        }
      } catch {
        setAgents(prev =>
          prev.map(a => (a.id === 'orquestador' ? { ...a, status: 'offline' } : a))
        );
      }
    };
    fetchStatus();
  }, []);

  const statusColor: Record<string, string> = {
    online: 'bg-emerald-500',
    offline: 'bg-destructive',
    'checking...': 'bg-amber-400',
  };

  return (
    <div className="h-full flex flex-col overflow-hidden bg-card">
      <div className="p-4 border-b border-border">
        <h2 className="font-semibold text-sm text-foreground flex items-center gap-2">
          <Terminal className="w-4 h-4 text-primary" />
          Centro de Control
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {agents.map(agent => (
          <button
            key={agent.id}
            onClick={() => setActiveAgent(agent.id)}
            className={`w-full text-left p-3 rounded-lg transition-all flex items-start gap-3 ${
              activeAgent === agent.id
                ? 'bg-primary/10 border border-primary/20'
                : 'hover:bg-secondary border border-transparent'
            }`}
          >
            <div
              className={`p-1.5 rounded-md flex-shrink-0 mt-0.5 ${
                activeAgent === agent.id
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-muted-foreground'
              }`}
            >
              <Bot className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div
                className={`text-sm font-medium leading-tight truncate ${
                  activeAgent === agent.id ? 'text-primary' : 'text-foreground'
                }`}
              >
                {agent.name}
              </div>
              <div className="flex items-center gap-1.5 mt-1">
                <span
                  className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                    statusColor[agent.status ?? ''] ?? 'bg-muted-foreground'
                  }`}
                />
                <span className="text-[11px] text-muted-foreground truncate">
                  {agent.status === 'online' && agent.model ? agent.model : agent.status}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default AgentSidebar;
