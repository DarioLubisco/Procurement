import { useState } from 'react';
import AgentSidebar from '@/components/AgentSidebar';
import ChatBox from '@/components/ChatBox';

const ChatView = () => {
  const [activeAgent, setActiveAgent] = useState<string>('orquestador');

  return (
    <div className="flex h-full overflow-hidden">
      {/* Agent Sidebar - left panel */}
      <div className="w-72 flex-shrink-0 border-r border-border bg-card overflow-hidden">
        <AgentSidebar activeAgent={activeAgent} setActiveAgent={setActiveAgent} />
      </div>

      {/* Chat Area - right panel */}
      <div className="flex-1 overflow-hidden">
        <ChatBox activeAgent={activeAgent} />
      </div>
    </div>
  );
};

export default ChatView;
