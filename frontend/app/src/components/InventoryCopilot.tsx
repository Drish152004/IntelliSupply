import { useState } from 'react';

type Message = {
  role: 'You' | 'Copilot';
  text: string;
  sql?: string;
  headers?: string[];
  rows?: string[][];
  emphasis?: string;
  detail?: string;
};

const quickChips = [
  'Top 5 products by revenue this month',
  'Show all stockout risk items',
  'Hub-wise sales breakdown',
  'How do delays impact Electronics sales?'
];

const responses: { match: string[]; message: Message }[] = [
  {
    match: ['revenue', 'top 5'],
    message: {
      role: 'Copilot',
      text: 'Top 5 products by revenue this month:',
      sql:
        "SELECT product_name, SUM(revenue) as rev FROM sales WHERE month='May-2025' GROUP BY product_name ORDER BY rev DESC LIMIT 5",
      headers: ['Product', 'Revenue', 'Margin'],
      rows: [
        ['Wireless Earbuds X3', 'INR 54.9L', '38%'],
        ['Paracetamol 500mg', 'INR 18.4L', '61%'],
        ['Laptop Stand Pro', 'INR 12.1L', '44%'],
        ['Basmati Rice 5kg', 'INR 9.6L', '22%'],
        ['Cotton T-Shirt (M)', 'INR 8.2L', '55%'],
      ],
    },
  },
  {
    match: ['stockout', 'risk'],
    message: {
      role: 'Copilot',
      text: 'Items at stockout risk right now:',
      sql:
        'SELECT product_name, hub, stock_level FROM inventory WHERE stock_level < reorder_point ORDER BY stock_level ASC',
      headers: ['Product', 'Hub', 'Stock Level'],
      rows: [
        ['USB-C Hub 7-in-1', 'Bengaluru', '0 units'],
        ['Wireless Earbuds X3', 'Mumbai', '42 units'],
        ['Vitamin C 1000mg', 'Delhi', '68 units'],
        ['Running Shoes (L)', 'Chennai', '71 units'],
        ['HDMI Cable 2m', 'Pune', '94 units'],
      ],
    },
  },
  {
    match: ['hub', 'breakdown'],
    message: {
      role: 'Copilot',
      text: 'Sales breakdown by hub:',
      sql:
        'SELECT hub, SUM(units) as units, SUM(revenue) as rev FROM sales GROUP BY hub ORDER BY rev DESC',
      headers: ['Hub', 'Units', 'Revenue'],
      rows: [
        ['Bengaluru', '14,200', 'INR 82.4L'],
        ['Mumbai', '12,810', 'INR 74.1L'],
        ['Delhi', '9,440', 'INR 58.9L'],
        ['Chennai', '7,620', 'INR 41.3L'],
        ['Pune', '4,250', 'INR 22.7L'],
      ],
    },
  },
  {
    match: ['delay', 'impact'],
    message: {
      role: 'Copilot',
      text: 'Delay impact on sales by category:',
      sql:
        'SELECT category, AVG(delay_days) as avg_delay, SUM(lost_revenue) as lost FROM shipments JOIN sales USING(sku) WHERE delayed=1 GROUP BY category',
      headers: ['Category', 'Avg Delay', 'Lost Revenue'],
      rows: [
        ['Electronics', '2.4 days', 'INR 6.8L'],
        ['Pharma', '1.1 days', 'INR 2.2L'],
        ['FMCG', '0.9 days', 'INR 1.4L'],
      ],
    },
  },
];

export default function InventoryCopilot({ isFocused, onToggleFocus }: { isFocused: boolean; onToggleFocus: () => void }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'Copilot',
      text: "Ask me anything about your inventory. I'll translate it to SQL and show you the results.",
    },
    { role: 'You', text: 'Which product sold the most last month?' },
    {
      role: 'Copilot',
      text: 'Top 3 products by units sold in April 2025:',
      sql:
        "SELECT product_name, SUM(units) as total\nFROM sales\nWHERE month = 'Apr-2025'\nGROUP BY product_name\nORDER BY total DESC LIMIT 3",
      headers: ['Product', 'Units', 'Revenue'],
      rows: [
        ['Paracetamol 500mg', '9,204', 'INR 18.4L'],
        ['Wireless Earbuds X3', '7,841', 'INR 54.9L'],
        ['Basmati Rice 5kg', '6,390', 'INR 9.6L'],
      ],
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);

  const buildResponse = (value: string): Message => {
    const query = value.toLowerCase();
    let match = responses.find((rule) => rule.match.every((token) => query.includes(token)));
    if (!match) {
      match = responses.find((rule) => rule.match.some((token) => query.includes(token)));
    }
    if (match) return match.message;
    return {
      role: 'Copilot',
      text: 'I understand you are asking about:',
      emphasis: value,
      detail:
        'Let me query the database. This would generate a live SQL query and return results from your inventory system.',
      sql:
        `-- Query generated from: "${value}"\nSELECT * FROM inventory\nWHERE /* parsed conditions */\nORDER BY relevance DESC;`,
    };
  };

  const send = (text: string) => {
    const value = text.trim();
    if (!value || isThinking) return;
    setMessages((prev) => [...prev, { role: 'You', kind: 'text', text: value }]);
    setInput('');
    setIsThinking(true);

    const response = buildResponse(value);

    setTimeout(() => {
      setIsThinking(false);
      setMessages((prev) => [...prev, response]);
    }, 900);
  };

  return (
    <aside className="right">
      <div className="chat-header">
        <div className="chat-header-info">
          <div className="chat-lbl">NLP to SQL Copilot</div>
          <div className="chat-title">Inventory Assistant</div>
          <div className="chat-sub">Plain English queries with demo SQL output</div>
        </div>
        <div className="chat-actions">
          <button className="btn-icon" onClick={onToggleFocus} title="Toggle Full Space">
            <svg 
              width="16" 
              height="16" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round"
              style={{ transform: isFocused ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s' }}
            >
              <polyline points="15 3 21 3 21 9"></polyline>
              <polyline points="9 21 3 21 3 15"></polyline>
              <line x1="21" y1="3" x2="14" y2="10"></line>
              <line x1="3" y1="21" x2="10" y2="14"></line>
            </svg>
          </button>
        </div>
      </div>

      <div className="chat-msgs custom-scrollbar">
        {messages.map((msg, idx) => (
          <div key={`${msg.role}-${idx}`} className={`msg ${msg.role === 'You' ? 'user' : 'bot'}`}>
            <div className="msg-role">{msg.role}</div>
            <div className="msg-bubble">
              <div className="msg-text">
                {msg.text}
                {msg.emphasis && <em> {msg.emphasis}</em>}
              </div>
              {msg.detail && <div className="msg-detail">{msg.detail}</div>}
              {msg.sql && <code className="sql-code">{msg.sql}</code>}
              {msg.headers && msg.rows && (
                <table className="res-table">
                  <thead>
                    <tr>
                      {msg.headers.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {msg.rows.map((row, rowIdx) => (
                      <tr key={`${row[0]}-${rowIdx}`}>
                        {row.map((cell, cellIdx) => (
                          <td key={`${rowIdx}-${cellIdx}`}>{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        ))}
        {isThinking && (
          <div className="msg bot">
            <div className="msg-role">Copilot</div>
            <div className="msg-bubble thinking">
              <span className="thinking-text">Thinking</span>
              <span className="typing-dot">.</span>
              <span className="typing-dot">.</span>
              <span className="typing-dot">.</span>
            </div>
          </div>
        )}
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
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Which category had highest return rate in Q1?"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
        />
        <button className="chat-send" onClick={() => send(input)}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
        </button>
      </div>
    </aside>
  );
}
