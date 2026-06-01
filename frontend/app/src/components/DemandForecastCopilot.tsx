import { useState } from 'react';

type DemandMessage = {
  role: 'You' | 'Copilot';
  text: string;
};

type DemandRule = {
  match: string[];
  response: string;
};

const quickQueries = [
  'Peak demand zones next week',
  'Expected volume for Bengaluru',
  'Weekend demand trend',
  'Capacity recommendation',
];

const demandRules: DemandRule[] = [
  {
    match: ['peak', 'zone'],
    response:
      'Peak pressure zones: Bengaluru (Wed, Score 94) and Delhi (Sun, Score 96). Recommend 12% extra courier allocation for these windows.',
  },
  {
    match: ['bengaluru', 'volume'],
    response:
      'Bengaluru forecast: 3,412 packages mid-week, tapering to 2,640 by weekend. Expect highest pressure Wed-Thu.',
  },
  {
    match: ['weekend', 'trend', 'sat', 'sun'],
    response:
      'Weekend demand is moderate with a spike in Delhi on Sunday. Average weekend volume is 18% lower than mid-week peaks.',
  },
  {
    match: ['capacity', 'recommendation', 'staffing'],
    response:
      'Capacity recommendation: Maintain 78% utilization. Add 6 couriers on Wed and Sun to avoid SLA risk.',
  },
  {
    match: ['forecast', 'next', 'week'],
    response:
      '7-day forecast (avg): 2,847 | 3,124 | 2,956 | 3,412 | 3,087 | 2,643 | 2,198. Peak demand on Day 4.',
  },
];

const fallbackResponse =
  'Try asking about peak zones, Bengaluru volume, weekend trend, or capacity recommendations.';

export default function DemandForecastCopilot() {
  const [messages, setMessages] = useState<DemandMessage[]>([
    {
      role: 'Copilot',
      text: 'Ask me about demand forecasting and capacity planning for the next week.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);

  const getResponse = (value: string) => {
    const query = value.toLowerCase();
    for (const rule of demandRules) {
      if (rule.match.some((token) => query.includes(token))) {
        return rule.response;
      }
    }
    return fallbackResponse;
  };

  const send = (text: string) => {
    const value = text.trim();
    if (!value || isThinking) return;

    setMessages((prev) => [...prev, { role: 'You', text: value }]);
    setInput('');
    setIsThinking(true);

    const response = getResponse(value);
    setTimeout(() => {
      setIsThinking(false);
      setMessages((prev) => [...prev, { role: 'Copilot', text: response }]);
    }, 800);
  };

  return (
    <div className="demand-bot">
      <div className="demand-bot-header">
        <div className="demand-bot-title">Demand Forecast Copilot</div>
        <div className="demand-bot-sub">Query peaks, zones, and capacity impacts</div>
      </div>

      <div className="demand-bot-messages custom-scrollbar">
        {messages.map((msg, idx) => (
          <div key={`${msg.role}-${idx}`} className={`demand-msg ${msg.role === 'You' ? 'user' : 'bot'}`}>
            <div className="demand-msg-role">{msg.role}</div>
            <div className="demand-msg-bubble">{msg.text}</div>
          </div>
        ))}
        {isThinking && (
          <div className="demand-msg bot">
            <div className="demand-msg-role">Copilot</div>
            <div className="demand-msg-bubble thinking">
              Thinking
              <span className="typing-dot">.</span>
              <span className="typing-dot">.</span>
              <span className="typing-dot">.</span>
            </div>
          </div>
        )}
      </div>

      <div className="demand-bot-chips">
        {quickQueries.map((chip) => (
          <button key={chip} className="demand-chip" onClick={() => send(chip)}>
            {chip}
          </button>
        ))}
      </div>

      <div className="demand-bot-input">
        <input
          className="demand-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about demand forecast"
        />
        <button className="demand-send" onClick={() => send(input)}>
          Send
        </button>
      </div>
    </div>
  );
}
