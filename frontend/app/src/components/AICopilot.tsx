import { useState, useRef, useEffect } from 'react';
import { MessageSquare, Trash2, Send, Mic, Sparkles, Bot, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { motion, AnimatePresence } from 'framer-motion';
import { initialChatMessages, suggestedPrompts } from '@/data/mockData';
import type { ChatMessage } from '@/data/mockData';

export default function AICopilot() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialChatMessages);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = () => {
    if (!inputValue.trim()) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsTyping(true);

    setTimeout(() => {
      setIsTyping(false);
      const responses = [
        'Analyzing your request... I found 2 optimized routes with 15% shorter transit times.',
        'Processing complete. Updated shipment priorities across 4 routes.',
        'Route analysis indicates congestion on NH-44. Suggesting alternate path via NH-69.',
        'All deliveries in the queried region are on schedule. No action needed.',
      ];
      const aiMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'ai',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    }, 1500);
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  const handleSuggestedPrompt = (prompt: string) => {
    setInputValue(prompt);
  };

  return (
    <div className="w-full border-r border-border bg-card flex flex-col h-full shrink-0">
      <div className="h-12 border-b border-border flex items-center justify-between px-3 shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">AI Logistics Copilot</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClearChat}
          className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
        >
          <Trash2 className="w-3 h-3 mr-1" />
          Clear
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-3">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                  msg.role === 'ai' ? 'bg-black/10' : 'bg-muted'
                }`}
              >
                {msg.role === 'ai' ? (
                  <Sparkles className="w-3 h-3 text-black" />
                ) : (
                  <User className="w-3 h-3 text-muted-foreground" />
                )}
              </div>
              <div
                className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                  msg.role === 'user' ? 'bg-black text-white rounded-br-sm' : 'bg-muted rounded-bl-sm'
                }`}
              >
                {msg.content}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        <AnimatePresence>
          {isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex gap-2"
            >
              <div className="w-6 h-6 rounded-full bg-black/10 flex items-center justify-center shrink-0">
                <Bot className="w-3 h-3 text-black" />
              </div>
              <div className="bg-muted rounded-xl rounded-bl-sm px-3 py-2.5 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full typing-dot" />
                <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full typing-dot" />
                <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full typing-dot" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={chatEndRef} />
      </div>

      <div className="px-3 pb-2">
        <div className="flex flex-wrap gap-1.5">
          {suggestedPrompts.slice(0, 1).map((prompt) => (
            <button
              key={prompt}
              onClick={() => handleSuggestedPrompt(prompt)}
              className="text-[10px] px-2 py-1 rounded-full bg-muted hover:bg-muted/80 text-muted-foreground transition-colors border border-border"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-2 bg-muted rounded-xl px-3 py-2 border border-border focus-within:border-primary/30 focus-within:ring-1 focus-within:ring-primary/10 transition-all">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type a command..."
            className="h-6 border-0 bg-transparent p-0 text-xs focus-visible:ring-0 placeholder:text-muted-foreground/60"
          />
          <Mic className="w-3.5 h-3.5 text-muted-foreground shrink-0 cursor-pointer hover:text-foreground transition-colors" />
          <Button
            size="icon"
            onClick={handleSend}
            disabled={!inputValue.trim()}
            className="h-6 w-6 rounded-lg shrink-0"
          >
            <Send className="w-3 h-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}
