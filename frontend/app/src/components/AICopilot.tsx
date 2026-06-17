import { useState, useRef, useEffect, useCallback } from 'react';
import { useSessionStorageState } from '@/hooks/useSessionStorage';
import { MessageSquare, Trash2, Send, Mic, MicOff, Sparkles, Bot, User, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { motion, AnimatePresence } from 'framer-motion';
import { suggestedPrompts } from '@/data/mockData';
import type { ChatMessage } from '@/data/mockData';
import { queryCopilot, transcribeVoice, type CopilotResponse } from '@/lib/api';
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

function buildVoiceUserMessage(original: string, english: string, lang?: string | null): string {
  if (!english.trim()) return original;
  if (!original.trim() || original.trim() === english.trim()) return english;
  const tag = lang ? ` (${lang.toUpperCase()})` : '';
  return `${original}${tag}\n→ ${english}`;
}

export default function AICopilot({ compact = false, expanded = false, domain = 'logistics' }: AICopilotProps) {
  const isCompact = compact && !expanded;
  const [messages, setMessages] = useSessionStorageState<ChatMessage[]>(`copilot_messages_${domain}`, []);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [logisticsSession, setLogisticsSession] = useSessionStorageState<Record<string, unknown> | null>('copilot_logistics_session', null);
  const [inventorySession, setInventorySession] = useSessionStorageState<Record<string, unknown> | null>('copilot_inventory_session', null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, isTranscribing]);

  useEffect(() => {
    return () => {
      mediaRecorderRef.current?.stop();
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const stopMediaStream = useCallback(() => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
  }, []);

  const sendQuery = useCallback(
    async (query: string, displayContent?: string) => {
      const trimmed = query.trim();
      if (!trimmed) return;

      const userMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content: displayContent ?? trimmed,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setInputValue('');
      setIsTyping(true);
      setVoiceError(null);

      try {
        if (!getAccessToken()) {
          throw new Error('Sign in with a real account to use the copilot.');
        }
        const response = await queryCopilot(trimmed, {
          logisticsSession: domain === 'logistics' ? logisticsSession : null,
          inventorySession: domain === 'inventory' ? inventorySession : null,
        });
        if (response.status === 'clarification_required') {
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
        } else {
          setLogisticsSession(null);
          setInventorySession(null);
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
    },
    [domain, inventorySession, logisticsSession],
  );

  const handleSend = async () => {
    if (!inputValue.trim()) return;
    await sendQuery(inputValue);
  };

  const processRecording = useCallback(
    async (blob: Blob) => {
      if (!blob.size) {
        setVoiceError('No audio captured. Try speaking closer to the microphone.');
        return;
      }

      setIsTranscribing(true);
      setVoiceError(null);

      try {
        if (!getAccessToken()) {
          throw new Error('Sign in with a real account to use voice input.');
        }

        const result = await transcribeVoice(blob, 'auto');
        const english = result.english_text?.trim();
        if (!english) {
          throw new Error('No speech detected. Please try again.');
        }

        const display = buildVoiceUserMessage(
          result.original_text,
          english,
          result.detected_language,
        );
        await sendQuery(english, display);
      } catch (error) {
        setVoiceError(error instanceof Error ? error.message : 'Voice input failed.');
      } finally {
        setIsTranscribing(false);
      }
    },
    [sendQuery],
  );

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }
    setIsRecording(false);
  }, []);

  const startRecording = useCallback(async () => {
    setVoiceError(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceError('Microphone is not supported in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];

      const preferredTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
      ];
      const mimeType = preferredTypes.find((type) => MediaRecorder.isTypeSupported(type));

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });
        stopMediaStream();
        mediaRecorderRef.current = null;
        void processRecording(blob);
      };

      recorder.onerror = () => {
        setVoiceError('Recording failed. Please try again.');
        stopRecording();
        stopMediaStream();
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      setVoiceError('Microphone permission denied or unavailable.');
      stopMediaStream();
    }
  }, [processRecording, stopMediaStream, stopRecording]);

  const handleMicToggle = () => {
    if (isTranscribing || isTyping) return;
    if (isRecording) {
      stopRecording();
    } else {
      void startRecording();
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setVoiceError(null);
    if (domain === 'inventory') {
      setInventorySession(null);
    } else {
      setLogisticsSession(null);
    }
  };

  const handleSuggestedPrompt = (prompt: string) => {
    setInputValue(prompt);
  };

  const micBusy = isRecording || isTranscribing;

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
              Speak in English, Spanish, French, Hindi, Tamil, or Malayalam — mic translates to English automatically.
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

        {isTranscribing && (
          <div className="flex items-center gap-2 text-muted-foreground text-xs px-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Translating speech to English...
          </div>
        )}

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

      {(voiceError || isRecording) && (
        <div className={cn('px-3 pb-1 text-xs', isRecording ? 'text-red-500' : 'text-red-600')}>
          {isRecording ? 'Recording… click mic again to stop and send' : voiceError}
        </div>
      )}

      <div className={cn('border-t border-border flex items-center gap-2 shrink-0', isCompact ? 'p-2' : 'p-3')}>
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void handleSend()}
          placeholder={isCompact ? 'Ask copilot...' : 'Ask about shipments, inventory, routes...'}
          className={cn('rounded-full', isCompact ? 'h-8 text-xs' : 'h-10')}
          disabled={micBusy || isTyping}
        />
        <Button
          size="icon"
          className={cn('rounded-full shrink-0', isCompact ? 'h-8 w-8' : 'h-10 w-10')}
          onClick={() => void handleSend()}
          disabled={micBusy || isTyping}
        >
          <Send className={cn(isCompact ? 'w-3.5 h-3.5' : 'w-4 h-4')} />
        </Button>
        <Button
          variant={isRecording ? 'destructive' : 'outline'}
          size="icon"
          className={cn('rounded-full shrink-0', isCompact ? 'h-8 w-8' : 'h-10 w-10')}
          onClick={handleMicToggle}
          disabled={isTranscribing || isTyping}
          title={isRecording ? 'Stop recording' : 'Speak (multilingual)'}
        >
          {isTranscribing ? (
            <Loader2 className={cn('animate-spin', isCompact ? 'w-3.5 h-3.5' : 'w-4 h-4')} />
          ) : isRecording ? (
            <MicOff className={cn(isCompact ? 'w-3.5 h-3.5' : 'w-4 h-4')} />
          ) : (
            <Mic className={cn(isCompact ? 'w-3.5 h-3.5' : 'w-4 h-4')} />
          )}
        </Button>
      </div>
    </div>
  );
}
