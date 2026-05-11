import { useMemo, useState } from 'react';

type Message = {
  role: 'You' | 'Copilot';
  text: string;
};

const quickChips = [
  'Top 5 products by revenue this month',
  'Show all stockout risk items',
  'Hub-wise sales breakdown',
  'How do delays impact Electronics sales?',
];

const cannedResponses = [
  'Top products by revenue this month are Wireless Earbuds X3, Paracetamol 500mg, and Laptop Stand Pro.',
  'Detected 5 stockout risk items. USB-C Hub 7-in-1 in Bengaluru is currently at 0 units.',
  'Bengaluru and Mumbai are leading in total revenue, followed by Delhi.',
  'Electronics has the highest delay impact with an average delay of 2.4 days.',
];

export default function InventoryCopilot() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'Copilot',
      text: "Ask me anything about your inventory. I'll translate it to SQL-like insights and show results.",
    },
    { role: 'You', text: 'Which product sold the most last month?' },
    { role: 'Copilot', text: 'Paracetamol 500mg leads with 9,204 units sold.' },
  ]);
  const [input, setInput] = useState('');

  const responseIndex = useMemo(() => messages.length % cannedResponses.length, [messages.length]);

  const send = (text: string) => {
    const value = text.trim();
    if (!value) return;
    setMessages((prev) => [...prev, { role: 'You', text: value }, { role: 'Copilot', text: cannedResponses[responseIndex] }]);
    setInput('');
  };

  return (
    <aside className="right">
      <div className="chat-header">
        <div className="chat-lbl">NLP → SQL Copilot</div>
        <div className="chat-title">Ask your inventory</div>
        <div className="chat-sub">Query in plain English · Results powered by Graph RAG</div>
      </div>

      <div className="chat-msgs custom-scrollbar">
        {messages.map((msg, idx) => (
          <div key={`${msg.role}-${idx}`} className={`msg ${msg.role === 'You' ? 'user' : 'bot'}`}>
            <div className="msg-role">{msg.role}</div>
            <div className="msg-bubble">{msg.text}</div>
          </div>
        ))}
      </div>

      <div className="chat-chips">
        {quickChips.map((chip) => (
          <button key={chip} className="chip" onClick={() => send(chip)}>
            {chip} →
          </button>
        ))}
      </div>

      <div className="chat-input-area">
        <textarea
          className="chat-textarea"
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Which category had highest return rate in Q1?"
        />
        <button className="chat-send" onClick={() => send(input)}>
          Send
        </button>
      </div>
    </aside>
  );
}
