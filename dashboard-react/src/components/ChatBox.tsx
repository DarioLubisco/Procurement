import { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2, Zap, X } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface Props {
  activeAgent: string;
}

const skillsList = [
  { cmd: '/improve', desc: 'Busca oportunidades de mejora en la arquitectura del código' },
  { cmd: '/grill', desc: 'Pon a prueba planes arquitectónicos mediante preguntas rigurosas' },
  { cmd: '/caveman', desc: 'Modo ultra-comprimido, elimina el texto de relleno' },
  { cmd: '/zoom', desc: 'Ajusta el nivel de detalle de la conversación' },
  { cmd: '/handoff', desc: 'Compacta el contexto para entregarlo a otro agente' },
  { cmd: '/referral', desc: 'Delega el trabajo a un experto o sub-agente' },
  { cmd: '/impeccable', desc: 'Aplica estándares de código rigurosos' },
  { cmd: '/svgl', desc: 'Busca o maneja recursos SVG vectoriales' },
  { cmd: '/diagnose', desc: 'Diagnóstico profundo y corrección de bugs complejos' },
  { cmd: '/tdd', desc: 'Desarrollo guiado por pruebas (Test-Driven Development)' },
  { cmd: '/prototype', desc: 'Construye prototipos rápidos para validar ideas y UI' },
  { cmd: '/bash-pro', desc: 'Especialista en scripts de Bash defensivos y automatización' },
  { cmd: '/python-pro', desc: 'Optimización y patrones avanzados en Python 3.12+' },
  { cmd: '/sql-pro', desc: 'Modelado avanzado y optimización de bases de datos SQL' },
  { cmd: '/dashboard', desc: 'Genera un panel analítico completo en un solo HTML' },
  { cmd: '/live-artifact', desc: 'Crea artefactos dinámicos conectados a datos en tiempo real' },
  { cmd: '/mermaid-pro', desc: 'Genera diagramas de arquitectura robustos con Mermaid' },
  { cmd: '/qa', desc: 'Sesión interactiva de control de calidad y reporte de bugs' },
  { cmd: '/open-spec', desc: 'Refactoring estricto de HTML plano a React/Tailwind usando OpenSpec' },
  { cmd: '/victory-mobile', desc: 'Optimiza Victory Charts para móviles (React Web + Tailwind)' },
];

const agentLabel: Record<string, string> = {
  orquestador: 'Orquestador Central',
  portero: 'Portero Central',
  agente_it: 'Sub-Agente IT',
  agente_equivalencias: 'Agente de Equivalencias',
};

const ChatBox: React.FC<Props> = ({ activeAgent }) => {
  const [messages, setMessages] = useState<Record<string, Message[]>>({
    orquestador: [{ id: '1', role: 'assistant', content: 'Hola, soy el Orquestador Central de Synapse. Sistema en línea.' }],
    portero: [{ id: '1', role: 'assistant', content: 'Portero V3.2 conectado vía n8n. Esperando consulta.' }],
    agente_it: [{ id: '1', role: 'assistant', content: 'Sub-Agente IT (DeepSeek V4) en línea. Monitoreo de logs y contenedores listo.' }],
    agente_equivalencias: [{ id: '1', role: 'assistant', content: 'Agente de Equivalencias (DeepSeek V4 Flash) en Debian en línea. Listo para clasificar data.' }],
  });
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSkills, setShowSkills] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const currentMessages = messages[activeAgent] || [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentMessages, isLoading]);

  // Close skills on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowSkills(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => ({ ...prev, [activeAgent]: [...(prev[activeAgent] || []), userMsg] }));
    setInput('');
    setIsLoading(true);
    inputRef.current?.focus();

    try {
      if (activeAgent === 'portero') {
        const sessionId = localStorage.getItem('portero_session') || crypto.randomUUID();
        localStorage.setItem('portero_session', sessionId);
        const res = await fetch('https://n8n.farmaciaamericana.es/webhook/0b2cece3-d2d4-4a41-b6a9-8e2254e4c9e8', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'sendMessage', sessionId, chatInput: userMsg.content }),
        });
        const data = await res.json();
        const botMsg: Message = { id: (Date.now() + 1).toString(), role: 'assistant', content: data.output || 'Respuesta vacía.' };
        setMessages(prev => ({ ...prev, [activeAgent]: [...(prev[activeAgent] || []), botMsg] }));
      } else {
        const agentName = agentLabel[activeAgent] ?? activeAgent;
        const res = await fetch(`/api/orquestador/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent: agentName, message: userMsg.content }),
        });
        const data = await res.json();
        const botMsg: Message = { id: (Date.now() + 1).toString(), role: 'assistant', content: data.reply || 'Error obteniendo respuesta.' };
        setMessages(prev => ({ ...prev, [activeAgent]: [...(prev[activeAgent] || []), botMsg] }));
      }
    } catch {
      const errorMsg: Message = { id: (Date.now() + 1).toString(), role: 'assistant', content: '⚠️ Error al comunicar con el agente. Verifica la conexión.' };
      setMessages(prev => ({ ...prev, [activeAgent]: [...(prev[activeAgent] || []), errorMsg] }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-card flex items-center justify-between flex-shrink-0">
        <div>
          <h3 className="font-semibold text-foreground text-sm">{agentLabel[activeAgent] ?? activeAgent}</h3>
          <p className="text-[11px] text-muted-foreground mt-0.5">Synapse AI Network</p>
        </div>
        {isLoading && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
            <span>Procesando...</span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
        {currentMessages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex gap-3 max-w-[85%] md:max-w-[75%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              {/* Avatar */}
              <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 self-end mb-0.5 ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-foreground border border-border'
              }`}>
                {msg.role === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
              </div>
              {/* Bubble */}
              <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground rounded-br-sm'
                  : 'bg-card border border-border text-foreground rounded-bl-sm shadow-sm'
              }`}>
                {msg.content}
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex gap-3 max-w-[75%]">
              <div className="w-7 h-7 rounded-full bg-secondary border border-border flex items-center justify-center flex-shrink-0 self-end mb-0.5">
                <Bot className="w-3.5 h-3.5 text-foreground" />
              </div>
              <div className="bg-card border border-border rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <div className="flex gap-1 items-center h-4">
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} className="h-2" />
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-border bg-card flex-shrink-0">
        <div className="relative max-w-4xl mx-auto">
          {/* Skills Popover */}
          {showSkills && (
            <div className="absolute bottom-full mb-3 left-0 w-80 bg-popover border border-border rounded-xl shadow-xl overflow-hidden z-20 flex flex-col max-h-72">
              <div className="px-4 py-2.5 border-b border-border bg-secondary/50 flex justify-between items-center">
                <span className="font-semibold text-[11px] text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <Zap className="w-3 h-3 text-primary" /> Antigravity Skills
                </span>
                <button onClick={() => setShowSkills(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="overflow-y-auto p-1.5 flex-1">
                {skillsList.map(skill => (
                  <button
                    key={skill.cmd}
                    onClick={() => { setInput(skill.cmd + ' '); setShowSkills(false); inputRef.current?.focus(); }}
                    className="w-full text-left px-3 py-2 hover:bg-secondary rounded-lg transition-colors flex flex-col gap-0.5 group"
                  >
                    <span className="font-mono text-[12px] font-semibold text-primary">{skill.cmd}</span>
                    <span className="text-[11px] text-muted-foreground leading-tight">{skill.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSkills(!showSkills)}
              title="Antigravity Master Skills"
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all border flex-shrink-0 ${
                showSkills
                  ? 'bg-primary/10 border-primary/30 text-primary'
                  : 'bg-secondary border-border text-muted-foreground hover:text-foreground hover:bg-secondary/80'
              }`}
            >
              <Zap className="w-4 h-4" />
            </button>

            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder={`Escribe a ${agentLabel[activeAgent] ?? activeAgent}...`}
              disabled={isLoading}
              className="flex-1 bg-background border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all disabled:opacity-50"
            />

            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="w-10 h-10 bg-primary text-primary-foreground rounded-xl flex items-center justify-center hover:bg-primary/90 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0 shadow-sm"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4 ml-0.5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatBox;
