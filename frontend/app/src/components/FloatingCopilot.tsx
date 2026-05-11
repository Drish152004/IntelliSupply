import { useEffect, useRef, useState } from 'react';
import { MessageSquare, X, Send, Bot, User, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type ChatMessage = {
  id: string;
  role: 'user' | 'ai';
  content: string;
};

type ResponseRule = {
  match: string[];
  response: string;
};

const responses: ResponseRule[] = [
  {
    match: ['optimize', 'route', 'routes'],
    response:
      'Route RT-2847 can reduce travel time by 12% via NH-69. Consolidating RT-2849 saves INR 4,200 in transport cost.',
  },
  {
    match: ['delivery', 'status', 'on-time'],
    response:
      'Delivery status (last 24h): 42 completed, 8 in progress, 2 delayed. On-time rate is 92.4%, up 3.2% MoM.',
  },
  {
    match: ['courier', 'performance', 'driver'],
    response:
      'Top couriers this week: Rajesh Kumar (28, 100% on-time), Priya Singh (25, 96%), Vikram Patel (22, 90.9%).',
  },
  {
    match: ['cost', 'savings', 'optimize'],
    response:
      'Cost optimization: Fuel usage can drop 8.2% with route smoothing. Projected annual savings: INR 2.8L.',
  },
  {
    match: ['inventory', 'stock', 'product'],
    response:
      'Inventory is stable across all hubs with 3 low-stock SKUs flagged. Open Inventory to drill into details.',
  },
  {
    match: ['forecast', 'demand', 'pressure'],
    response:
      'Demand forecast shows a mid-week spike in Bengaluru and Delhi. Open Insights to review the heatmap details.',
  },
];

const fallbackResponse =
  'Ask about routes, delivery status, courier performance, or cost optimization.';

export default function FloatingCopilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-0',
      role: 'ai',
      content:
        'I can help with operations, delivery performance, and optimization. Ask a question to get started.',
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const getResponse = (input: string) => {
    const query = input.toLowerCase();
    for (const rule of responses) {
      if (rule.match.some((token) => query.includes(token))) {
        return rule.response;
      }
    }
    return fallbackResponse;
  };

  const handleSend = () => {
    const value = inputValue.trim();
    if (!value || isThinking) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: value,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsThinking(true);

    const response = getResponse(value);

    setTimeout(() => {
      setIsThinking(false);
      const aiMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'ai',
        content: response,
      };
      setMessages((prev) => [...prev, aiMsg]);
    }, 900);
  };

  return (
    <>
      <motion.button
        onClick={() => setIsOpen((prev) => !prev)}
        className="fixed bottom-5 right-5 z-40 h-12 w-12 rounded-full bg-black text-white shadow-[0_12px_32px_rgba(0,0,0,0.25)] ring-1 ring-black/10 hover:bg-neutral-900 focus:outline-none"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.96 }}
        aria-label="Open Copilot"
      >
        {isOpen ? <X className="h-5 w-5 mx-auto" /> : <Bot className="h-5 w-5 mx-auto" />}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.2 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black z-40"
              onClick={() => setIsOpen(false)}
            />
            <motion.aside
              initial={{ x: 420, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 420, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 260, damping: 28 }}
              className="fixed right-5 top-20 bottom-6 z-50 w-[380px] bg-white border border-border rounded-2xl shadow-[0_25px_60px_rgba(15,23,42,0.2)] flex flex-col overflow-hidden"
            >
              <div className="px-5 py-4 border-b border-border bg-[#f7f7f8]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-2xl bg-black text-white flex items-center justify-center shadow-sm">
                      <Sparkles className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-foreground">IntelliSupply Copilot</div>
                      <div className="text-xs text-muted-foreground">Operations, routes, and performance</div>
                    </div>
                  </div>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="h-8 w-8 rounded-full border border-border hover:bg-white transition-colors flex items-center justify-center"
                    aria-label="Close Copilot"
                  >
                    <X className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto custom-scrollbar px-5 py-4 space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                  >
                    <div
                      className={`h-7 w-7 rounded-full flex items-center justify-center border ${
                        msg.role === 'ai' ? 'border-border bg-white' : 'border-foreground bg-foreground'
                      }`}
                    >
                      {msg.role === 'ai' ? (
                        <Bot className="h-3.5 w-3.5 text-foreground" />
                      ) : (
                        <User className="h-3.5 w-3.5 text-white" />
                      )}
                    </div>
                    <div
                      className={`max-w-[75%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed border shadow-sm ${
                        msg.role === 'user'
                          ? 'bg-foreground text-background border-foreground'
                          : 'bg-white text-foreground border-border'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}

                {isThinking && (
                  <div className="flex gap-2">
                    <div className="h-7 w-7 rounded-full border border-border bg-white flex items-center justify-center">
                      <Bot className="h-3.5 w-3.5 text-foreground" />
                    </div>
                    <div className="rounded-2xl px-3 py-2 text-xs border border-border bg-white text-foreground flex items-center gap-1">
                      <span className="text-muted-foreground">Thinking</span>
                      <span className="typing-dot">.</span>
                      <span className="typing-dot">.</span>
                      <span className="typing-dot">.</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <div className="p-4 border-t border-border bg-white">
                <div className="flex items-center gap-2">
                  <Input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="Ask a question"
                    className="h-9 text-xs"
                    disabled={isThinking}
                  />
                  <Button
                    onClick={handleSend}
                    disabled={!inputValue.trim() || isThinking}
                    className="h-9 w-9 p-0 bg-black text-white hover:bg-neutral-900"
                  >
                    <Send className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
