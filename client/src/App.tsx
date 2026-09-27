import { useState, useRef, useEffect } from "react";
import { Send, Settings } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [models, setModels] = useState<string[]>(["qwen2.5-coder:7b"]);
  const [selectedModel, setSelectedModel] = useState<string>("qwen2.5-coder:7b");
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  useEffect(() => scrollToBottom(), [messages, loading]);

  useEffect(() => {
    fetch("http://localhost:8000/models")
      .then(res => res.json())
      .then(data => {
        if (data?.models?.length > 0) {
          const names = data.models.map((m: { name: string }) => m.name);
          setModels(names);
          if (data.current_model && names.includes(data.current_model)) {
            setSelectedModel(data.current_model);
          } else {
            setSelectedModel(names[0]);
          }
        }
      })
      .catch(err => console.error("Failed to fetch models:", err));
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    let currentResponse = "";
    const aiId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: aiId, role: "assistant", content: "" }]);

    try {
      const res = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.content, session_id: sessionId, model: selectedModel })
      });

      if (!res.body) throw new Error("No response body");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const chunk = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.token) {
                  currentResponse += data.token;
                  setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: currentResponse } : m));
                }
                if (data.done) {
                  if (data.session_id) setSessionId(data.session_id);
                }
              } catch (err) {
                console.error("Failed to parse chunk:", line);
              }
            }
          }
          boundary = buffer.indexOf("\n\n");
        }
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { id: Date.now().toString(), role: "assistant", content: "Error connecting to server." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-bgDark rounded-xl border border-borderDark overflow-hidden">
      <div 
        style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
        className="flex items-center justify-between px-4 py-3 bg-bgHeader select-none"
      >
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-accent"></div>
          <span className="font-semibold text-sm">AI Assistant</span>
        </div>
      </div>

      <div className="flex items-center gap-3 px-4 py-2 bg-bgPanel border-b border-borderDark">
        <span className="text-textSec text-xs font-medium uppercase tracking-wider">Model</span>
        <select 
          className="bg-bgDark text-textPri text-sm rounded border border-borderDark px-2 py-1 outline-none"
          value={selectedModel}
          onChange={e => setSelectedModel(e.target.value)}
        >
          {models.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-lg px-4 py-2 text-sm leading-relaxed ${
              msg.role === 'user' ? 'bg-accent text-white' : 'bg-bgPanel text-textPri border border-borderDark'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 bg-bgPanel border-t border-borderDark">
        <div className="flex items-end gap-2 bg-bgDark border border-borderDark rounded-lg p-2 focus-within:border-accent/50 transition-colors">
          <textarea
            className="flex-1 bg-transparent text-textPri text-sm resize-none outline-none max-h-32 min-h-[40px] px-2 py-2"
            placeholder="Message AI Assistant..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
          />
          <button 
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="p-2 text-accent hover:bg-accent/10 rounded-md disabled:opacity-50 disabled:hover:bg-transparent transition-colors mb-0.5"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}