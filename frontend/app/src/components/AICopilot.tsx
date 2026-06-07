import { useState, useRef, useEffect } from 'react';
import { MessageSquare, Trash2, Send, Mic, Sparkles, Bot, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { motion, AnimatePresence } from 'framer-motion';
import { suggestedPrompts } from '@/data/mockData';
import type { ChatMessage } from '@/data/mockData';
import { queryCopilot, type CopilotResponse } from '@/lib/api';
import { getAccessToken } from '@/lib/api';

interface AICopilotProps {
  compact?: boolean;
  expanded?: boolean;
  domain?: 'inventory' | 'logistics';
}

function formatCopilotReply(response: CopilotResponse): string {
  if (response.status === 'access_denied') {
    return response.reason ?? response.message ?? 'Access denied for this request.';
  }
  if (response.status === 'error') {
    return response.message ?? 'Something went wrong while processing your request.';
  }
  if (response.status === 'clarification_required') {
    return response.question ?? response.message ?? 'Please provide more details to continue.';
  }
  if (typeof response.answer === 'string' && response.answer.trim()) {
    return response.answer;
  }
  if (response.data && typeof response.data === 'object') {
    const data = response.data as Record<string, unknown>;
    if (typeof data.answer === 'string' && data.answer.trim()) {
      return data.answer;
    }
    if (typeof data.message === 'string' && data.message.trim()) {
      return data.message;
    }
  }
  if (typeof response.message === 'string' && response.message.trim()) {
    return response.message;
  }
  if (response.data && typeof response.data === 'object') {
    return JSON.stringify(response.data, null, 2);
  }
  return 'Request processed successfully.';
}

export default function AICopilot({ compact = false, expanded = false, domain = 'logistics' }: AICopilotProps) {
  const isCompact = compact && !expanded;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [logisticsSession, setLogisticsSession] = useState<Record<string, unknown> | null>(null);
  const [inventorySession, setInventorySession] = useState<Record<string, unknown> | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    const query = inputValue;
    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsTyping(true);

    try {
      if (!getAccessToken()) {
        throw new Error('Sign in with a real account to use the copilot.');
      }
      const response = await queryCopilot(query, {
        logisticsSession: domain === 'logistics' ? logisticsSession : null,
        inventorySession: domain === 'inventory' ? inventorySession : null,
      });
      if (response.data && typeof response.data === 'object') {
        const session = (response.data as Record<string, unknown>).session;
        if (session && typeof session === 'object') {
          if (domain === 'inventory') {
            setInventorySession(session as Record<string, unknown>);
          } else {
            setLogisticsSession(session as Record<string, unknown>);
          }
        }
      }
      const aiMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'ai',
        content: formatCopilotReply(response),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error) {
      const aiMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'ai',
        content: error instanceof Error ? error.message : 'Unable to reach copilot service.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    if (domain === 'inventory') {
      setInventorySession(null);
    } else {
      setLogisticsSession(null);
    }
  };

  const handleSuggestedPrompt = (prompt: string) => {
    setInputValue(prompt);
  };

  return (
    <div
      className={cn(
        'w-full bg-card flex flex-col shrink-0 h-full',
        isCompact && 'overflow-hidden',
        !compact && 'border-r border-border',
      )}
    >
      <div className={cn('border-b border-border flex items-center justify-between px-3 shrink-0', isCompact ? 'h-9' : 'h-12')}>
        <div className="flex items-center gap-2">
          <MessageSquare className={cn('text-primary', isCompact ? 'w-3.5 h-3.5' : 'w-4 h-4')} />
          <span className={cn('font-semibold', isCompact ? 'text-xs' : 'text-sm')}>AI Copilot</span>
          {!isCompact && (
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
              Live
            </span>
          )}
        </div>
        <Button variant="ghost" size="icon" className={cn(isCompact ? 'h-7 w-7' : 'h-8 w-8')} onClick={handleClearChat}>
          <Trash2 className={cn(isCompact ? 'w-3 h-3' : 'w-3.5 h-3.5')} />
        </Button>
      </div>

      <div className={cn('flex-1 overflow-y-auto space-y-3', isCompact ? 'p-2' : 'p-4')}>
        {messages.length === 0 && (
          <div className={cn('rounded-2xl border border-dashed border-border bg-muted/30', isCompact ? 'p-3' : 'p-4')}>
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-primary" />
              <p className={cn('font-medium', isCompact ? 'text-xs' : 'text-sm')}>Ask about inventory, routes, or ETA</p>
            </div>
            <p className={cn('text-muted-foreground', isCompact ? 'text-[11px]' : 'text-xs')}>
              Your role permissions are enforced server-side via JWT.
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn('flex gap-2', msg.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              {msg.role === 'ai' && (
                <div className={cn('rounded-full bg-primary/10 flex items-center justify-center shrink-0', isCompact ? 'w-6 h-6' : 'w-8 h-8')}>
                  <Bot className={cn('text-primary', isCompact ? 'w-3 h-3' : 'w-4 h-4')} />
                </div>
              )}
              <div
                className={cn(
                  'rounded-2xl px-3 py-2 max-w-[85%] whitespace-pre-wrap',
                  msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground',
                  isCompact ? 'text-[11px]' : 'text-sm',
                )}
              >
                {msg.content}
              </div>
              {msg.role === 'user' && (
                <div className={cn('rounded-full bg-muted flex items-center justify-center shrink-0', isCompact ? 'w-6 h-6' : 'w-8 h-8')}>
                  <User className={cn('text-muted-foreground', isCompact ? 'w-3 h-3' : 'w-4 h-4')} />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {isTyping && (
          <div className="flex items-center gap-2 text-muted-foreground text-xs px-2">
            <Bot className="w-4 h-4" />
            Copilot is thinking...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {!isCompact && (
        <div className="px-4 pb-2 flex flex-wrap gap-2">
          {suggestedPrompts.slice(0, 3).map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => handleSuggestedPrompt(prompt)}
              className="text-[11px] rounded-full border border-border px-3 py-1 text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      <div className={cn('border-t border-border flex items-center gap-2 shrink-0', isCompact ? 'p-2' : 'p-3')}>
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void handleSend()}
          placeholder={isCompact ? 'Ask copilot...' : 'Ask about shipments, inventory, routes...'}
          className={cn('rounded-full', isCompact ? 'h-8 text-xs' : 'h-10')}
        />
        <Button size="icon" className={cn('rounded-full shrink-0', isCompact ? 'h-8 w-8' : 'h-10 w-10')} onClick={() => void handleSend()}>
          <Send className={cn(isCompact ? 'w-3.5 h-3.5' : 'w-4 h-4')} />
        </Button>
        {!isCompact && (
          <Button variant="outline" size="icon" className="rounded-full h-10 w-10 shrink-0" disabled>
            <Mic className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
