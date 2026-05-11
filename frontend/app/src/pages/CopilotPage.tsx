import { useState, useRef, useEffect } from 'react';
import { Send, Trash2, Bot, User, Brain } from 'lucide-react';
import Navbar from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  thinking?: string;
  timestamp: Date;
}

const supplyChainResponses: Record<string, string> = {
  'optimize routes': 'I\'ve analyzed all active routes and identified 3 optimization opportunities:\n\n1. Route RT-2847 can save 12% fuel by rerouting through NH-69\n2. Consolidating shipments on Route RT-2849 could reduce transport cost by ₹4,200\n3. Adjusting departure time for Route RT-2851 by 2 hours avoids peak traffic congestion',
  'inventory levels': 'Current inventory status:\n• Paracetamol 500mg: 9,204 units (19.0%) - In Stock\n• Wireless Earbuds X3: 7,841 units (16.2%) - Low Stock ⚠️\n• Basmati Rice 5kg: 6,390 units (13.2%) - In Stock\n• USB-C Hub 7-in-1: 4,120 units (8.5%) - Critical Stockout 🔴\n\nRecommended action: Reorder USB-C Hub immediately to prevent fulfillment delays.',
  'delivery status': 'Summary of deliveries in the last 24 hours:\n• Completed: 42 deliveries (92.4% on-time)\n• In Progress: 8 deliveries (6 on-time, 2 delayed)\n• Failed/Pending: 2 deliveries (weather-related delays)\n\nOn-time delivery rate is excellent at 92.4%, up 3.2% from last month.',
  'courier performance': 'Top performing couriers this week:\n1. Rajesh Kumar - 28 deliveries, 100% on-time rate\n2. Priya Singh - 25 deliveries, 96% on-time rate\n3. Vikram Patel - 22 deliveries, 90.9% on-time rate\n\nCouriers needing support:\n• Suresh Reddy - 18 deliveries, 72% on-time rate (3 delays on Route RT-2848)',
  'cost optimization': 'Identified cost optimization opportunities:\n• Fuel expenses: 8.2% reduction possible through route optimization\n• Vehicle maintenance: Schedule 3 vehicles for preventive maintenance\n• Staff efficiency: Cross-train 5 couriers for better scheduling flexibility\n• Logistics network: Consolidate 2 underutilized hubs into primary network\n\nProjected savings: ₹2.8L annually',
};

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-0',
      role: 'ai',
      content: 'Hello! I\'m your Supply Chain AI Copilot. I can help you with inventory management, route optimization, delivery tracking, courier performance, and cost analysis. What would you like to know?',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, isThinking]);

  const generateThinking = (query: string): string => {
    const thinkingStates = [
      `Analyzing supply chain data for: "${query}". Querying inventory database... Checking route metrics... Reviewing delivery statistics...`,
      `Processing query about supply chain. Fetching real-time logistics data... Cross-referencing with historical patterns... Calculating optimization recommendations...`,
      `Examining "${query}" in context of current operations. Loading warehouse inventory... Analyzing transportation network... Computing performance metrics...`,
      `Searching knowledge base for supply chain insights. Correlating with current shipment status... Evaluating risk factors... Formulating recommendations...`,
    ];
    return thinkingStates[Math.floor(Math.random() * thinkingStates.length)];
  };

  const getResponse = (query: string): string => {
    const lowerQuery = query.toLowerCase();
    
    for (const [key, response] of Object.entries(supplyChainResponses)) {
      if (lowerQuery.includes(key)) {
        return response;
      }
    }
    
    const genericResponses = [
      'I\'ve processed your request against our supply chain database. Based on current operational metrics, I recommend reviewing route efficiency and inventory turnover rates. Would you like specific data on any aspect?',
      'Analyzing your query across logistics, inventory, and delivery networks. Key insights: our network is operating at 94% efficiency, with optimal distribution across regional hubs. Need more details on a specific area?',
      'Your question touches on supply chain optimization. I\'m recommending a comprehensive audit of procurement cycles and last-mile delivery patterns. What specific metric interests you most?',
    ];
    
    return genericResponses[Math.floor(Math.random() * genericResponses.length)];
  };

  const handleSend = () => {
    if (!inputValue.trim()) return;

    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsThinking(true);

    // Show thinking for 2-3 seconds
    setTimeout(() => {
      setIsThinking(false);
      setIsTyping(true);
    }, 2000 + Math.random() * 1000);

    // Show response after thinking
    setTimeout(() => {
      setIsTyping(false);
      const aiMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'ai',
        content: getResponse(inputValue),
        thinking: generateThinking(inputValue),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    }, 3500 + Math.random() * 1500);
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: 'msg-0',
        role: 'ai',
        content: 'Hello! I\'m your Supply Chain AI Copilot. I can help you with inventory management, route optimization, delivery tracking, courier performance, and cost analysis. What would you like to know?',
        timestamp: new Date(),
      },
    ]);
  };

  const quickQueries = [
    'Optimize routes',
    'Inventory levels',
    'Delivery status',
    'Courier performance',
  ];

  return (
    <div className="h-screen bg-white text-black flex flex-col overflow-hidden">
      <Navbar />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="border-b border-gray-200 px-8 py-4 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-black flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-black">Supply Chain Copilot</h1>
                <p className="text-sm text-gray-600">AI-powered logistics intelligence</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearChat}
              className="text-xs"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear Chat
            </Button>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6 custom-scrollbar">
          <AnimatePresence mode="popLayout">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    msg.role === 'ai'
                      ? 'bg-black'
                      : 'bg-gray-200'
                  }`}
                >
                  {msg.role === 'ai' ? (
                    <Bot className="w-5 h-5 text-white" />
                  ) : (
                    <User className="w-5 h-5 text-gray-600" />
                  )}
                </div>

                {/* Message Content */}
                <div className={`max-w-2xl ${msg.role === 'user' ? '' : 'space-y-2'}`}>
                  {msg.thinking && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="bg-gray-50 border border-gray-200 rounded-lg p-3"
                    >
                      <div className="flex items-start gap-2">
                        <Brain className="w-4 h-4 text-gray-600 mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="text-xs font-semibold text-gray-700 mb-1">Thinking...</p>
                          <p className="text-xs text-gray-600 italic">{msg.thinking}</p>
                        </div>
                      </div>
                    </motion.div>
                  )}
                  
                  <div
                    className={`rounded-lg px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                      msg.role === 'user'
                        ? 'bg-black text-white rounded-br-none'
                        : 'bg-gray-100 text-gray-900 rounded-bl-none border border-gray-200'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              </motion.div>
            ))}

            {/* Thinking State */}
            {isThinking && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-4"
              >
                <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center shrink-0">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 max-w-2xl">
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-gray-600" />
                    <p className="text-xs font-semibold text-gray-700">Thinking...</p>
                  </div>
                  <div className="flex gap-1.5 mt-2">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
                  </div>
                </div>
              </motion.div>
            )}

            {/* Typing State */}
            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-4"
              >
                <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center shrink-0">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div className="bg-gray-100 border border-gray-200 rounded-lg rounded-bl-none px-4 py-3">
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
                    <span className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    <span className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={chatEndRef} />
        </div>

        {/* Quick Queries */}
        {messages.length <= 1 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="px-8 pb-4"
          >
            <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">
              Try asking about:
            </p>
            <div className="flex flex-wrap gap-2">
              {quickQueries.map((query) => (
                <button
                  key={query}
                  onClick={() => setInputValue(query)}
                  className="text-xs px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200 transition-colors"
                >
                  {query}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Input Area */}
        <div className="border-t border-gray-200 px-8 py-4 bg-white">
          <div className="max-w-4xl mx-auto flex gap-3">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
              placeholder="Ask me anything about your supply chain... (Shift+Enter for new line)"
              className="flex-1 border-gray-300 focus:ring-0 focus:border-black"
            />
            <Button
              onClick={handleSend}
              disabled={!inputValue.trim() || isTyping || isThinking}
              className="bg-black hover:bg-gray-900 text-white"
              size="icon"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
