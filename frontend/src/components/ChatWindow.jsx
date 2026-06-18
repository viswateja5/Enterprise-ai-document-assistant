import React, { useState, useRef, useEffect } from 'react';
import { Send, FileText, Bot, User, Link, Copy, Check } from 'lucide-react';

export default function ChatWindow({ 
  messages, 
  onSendMessage, 
  isLoading,
  activeDocument 
}) {
  const [input, setInput] = useState('');
  const [copiedIdx, setCopiedIdx] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-grow textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSuggestionClick = (text) => {
    setInput(text);
    textareaRef.current?.focus();
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => {
      setCopiedIdx(null);
    }, 2000);
  };

  const suggestions = [
    "What is the main summary of the document?",
    "List all key findings or metrics reported.",
    "Are there any actions or steps recommended?",
    "Summarize the conclusion section."
  ];

  return (
    <div className="flex-1 flex flex-col bg-[#212121] h-full relative overflow-hidden font-sans">
      {/* Active Context Ribbon */}
      <div className="w-full h-12 border-b border-[#2f2f2f] bg-[#212121]/80 backdrop-blur-md px-6 flex items-center justify-between text-xs text-gray-400 shrink-0">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-emerald-400" />
          <span>Active Context:</span>
          <span className="font-semibold text-gray-200">
            {activeDocument ? activeDocument.name : "Active Vector DB (Multi-Doc Search Active)"}
          </span>
        </div>
        {!activeDocument && (
          <span className="text-emerald-400/80 font-medium">Multi-PDF Ingestion Active</span>
        )}
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto px-4 md:px-0 py-6 scroll-smooth">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            /* Empty State */
            <div className="h-full flex flex-col items-center justify-center text-center pt-12 md:pt-20">
              <div className="w-12 h-12 bg-emerald-950/40 rounded-full flex items-center justify-center border border-emerald-800/30 mb-4 shadow-[0_0_15px_rgba(16,185,129,0.1)]">
                <Bot className="w-6 h-6 text-emerald-400" />
              </div>
              <h2 className="text-2xl md:text-3xl font-extrabold text-gray-100 mb-2 tracking-tight">
                Enterprise AI Document Assistant
              </h2>
              <p className="text-sm text-gray-400 max-w-md mb-8">
                Upload PDFs, Word Docs, or TXT documents. Hybrid retrieval search and semantic cross-encoder reranking are active automatically.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl px-4">
                {suggestions.map((sug, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSuggestionClick(sug)}
                    className="p-4 rounded-2xl bg-[#2f2f2f] hover:bg-[#363636] border border-[#3c3c3c] text-left text-xs md:text-sm text-gray-300 hover:text-white transition-all duration-150 focus:outline-none"
                  >
                    {sug}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              return (
                <div 
                  key={idx} 
                  className={`flex space-x-4 animate-fade-in ${
                    isUser ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {/* Left Bot Icon */}
                  {!isUser && (
                    <div className="w-8 h-8 rounded-full bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center shrink-0 shadow-[0_2px_5px_rgba(0,0,0,0.2)]">
                      <Bot className="w-4 h-4 text-emerald-400" />
                    </div>
                  )}

                  {/* Message Bubble */}
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 leading-relaxed text-sm md:text-base group relative ${
                    isUser 
                      ? 'bg-emerald-600 text-white rounded-br-none shadow-[0_2px_8px_rgba(16,185,129,0.15)]' 
                      : 'bg-[#2f2f2f] text-gray-200 rounded-bl-none border border-[#3a3a3a] shadow-sm'
                  }`}>
                    {/* Render message body content */}
                    <div className="whitespace-pre-wrap select-text selection:bg-emerald-800 selection:text-white">
                      {msg.content}
                    </div>

                    {/* Copy Response Button (for bot responses) */}
                    {!isUser && (
                      <button
                        onClick={() => handleCopy(msg.content, idx)}
                        className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-[#212121] hover:bg-black/40 border border-[#424242] text-gray-400 hover:text-white transition-all focus:outline-none"
                        title="Copy Response"
                      >
                        {copiedIdx === idx ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}

                    {/* Source Citations */}
                    {!isUser && msg.sources && msg.sources.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-[#3c3c3c] flex flex-col space-y-1.5">
                        <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider flex items-center space-x-1">
                          <Link className="w-3 h-3 text-emerald-400" />
                          <span>Sources Cited ({msg.sources.length})</span>
                        </span>
                        <div className="flex flex-wrap gap-2 pt-1">
                          {msg.sources.map((src, sIdx) => (
                            <div 
                              key={sIdx} 
                              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-[#212121] hover:bg-[#1a1a1a] border border-[#3e3e3e] text-[11px] text-emerald-400 transition-colors"
                              title={`Chunk ID: ${src.chunk_id}`}
                            >
                              <FileText className="w-3.5 h-3.5 shrink-0 text-emerald-500" />
                              <span className="truncate max-w-[120px] font-medium text-gray-300">{src.file}</span>
                              <span className="text-[10px] text-emerald-500 font-bold bg-emerald-950 px-1 rounded">
                                {src.page === 'Web' || src.page === '0' ? 'Web' : `Page ${src.page}`}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right User Icon */}
                  {isUser && (
                    <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center shrink-0 shadow-[0_2px_5px_rgba(0,0,0,0.2)]">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              );
            })
          )}

          {/* Typing Indicator */}
          {isLoading && (
            <div className="flex space-x-4 justify-start">
              <div className="w-8 h-8 rounded-full bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="bg-[#2f2f2f] border border-[#3a3a3a] rounded-2xl rounded-bl-none px-4 py-3 shadow-sm flex items-center space-x-1.5 min-w-[70px]">
                <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full typing-dot"></span>
                <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full typing-dot"></span>
                <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full typing-dot"></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Box Area */}
      <div className="p-4 border-t border-[#2f2f2f] bg-[#212121] shrink-0">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative">
          <div className="relative rounded-2xl bg-[#2f2f2f] border border-[#3c3c3c] transition-all focus-within:border-emerald-600 focus-within:shadow-[0_0_15px_rgba(16,185,129,0.08)] flex items-end">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about the document context..."
              disabled={isLoading}
              className="flex-1 max-h-[200px] min-h-[44px] py-3.5 px-4 bg-transparent outline-none border-none text-sm md:text-base text-gray-200 placeholder-gray-500 resize-none font-sans"
            />
            <div className="p-2.5">
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="w-8 h-8 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center transition-all shadow-[0_2px_6px_rgba(16,185,129,0.2)] focus:outline-none"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          <p className="text-[10px] text-center text-gray-500 mt-2">
            RAG Chatbot answers based strictly on retrieved documents. Verify critical details.
          </p>
        </form>
      </div>
    </div>
  );
}
