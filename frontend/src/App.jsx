import React, { useState, useEffect } from 'react';
import { Menu, X, Database } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import { fetchSessions, fetchSessionHistory, deleteSession, queryStream } from './api';

// Simple helper to generate unique session IDs for new client sessions
const generateSessionId = () => `session_${Math.random().toString(36).substring(2, 9)}`;

export default function App() {
  const [view, setView] = useState('login'); // 'login' | 'register' | 'chat' | 'dashboard'
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [sessions, setSessions] = useState([]);
  const [allMessages, setAllMessages] = useState({}); // Mapped by sessionId: { [sessId]: [...] }
  const [activeDocument, setActiveDocument] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Authenticate on mount checking local storage rag_token
  useEffect(() => {
    const token = localStorage.getItem('rag_token');
    if (token) {
      setIsAuthenticated(true);
      setView('chat');
    } else {
      setIsAuthenticated(false);
      setView('login');
    }
  }, []);

  // Load user sessions from database when entering 'chat' view
  useEffect(() => {
    if (view === 'chat') {
      loadSessions(true);
    }
  }, [view]);

  const loadSessions = async (autoSelect = true) => {
    try {
      const data = await fetchSessions();
      setSessions(data);
      
      const newAllMessages = {};
      data.forEach(sess => {
        newAllMessages[sess.id] = sess.messages || [];
      });
      setAllMessages(newAllMessages);

      if (autoSelect) {
        if (data.length > 0) {
          // Select the most recent session
          setSessionId(data[0].id);
        } else {
          // Fallback to auto-starting a session if list is empty
          const newId = generateSessionId();
          setSessionId(newId);
          setSessions([{ id: newId, name: 'New Conversation' }]);
          setAllMessages({ [newId]: [] });
        }
      }
    } catch (err) {
      console.error("Failed to fetch sessions from server:", err);
      // Auto-redirect to login on session authentication rejection
      if (err.response?.status === 401) {
        handleLogout();
      }
    }
  };

  const handleSelectSession = async (id) => {
    setSessionId(id);
    setMobileMenuOpen(false);
    
    // Fetch latest message logs from db for accuracy
    try {
      const data = await fetchSessionHistory(id);
      setAllMessages(prev => ({
        ...prev,
        [id]: data.messages || []
      }));
    } catch (err) {
      // If session doesn't exist yet on backend (unsaved local new session), keep it empty
      if (err.response?.status !== 404) {
        console.error(`Failed to load history for session ${id}:`, err);
      }
    }
  };

  const handleNewChat = () => {
    const newId = generateSessionId();
    setSessionId(newId);
    setSessions(prev => [
      { id: newId, name: 'New Conversation' },
      ...prev
    ]);
    setAllMessages(prev => ({
      ...prev,
      [newId]: []
    }));
    setMobileMenuOpen(false);
  };

  const handleDeleteSession = async (id) => {
    try {
      try {
        await deleteSession(id);
      } catch (err) {
        // Suppress 404 in case it is a client-only session that hasn't been saved in db yet
        if (err.response?.status !== 404) {
          throw err;
        }
      }
      
      setSessions(prev => {
        const filtered = prev.filter(s => s.id !== id);
        if (id === sessionId) {
          if (filtered.length > 0) {
            setSessionId(filtered[0].id);
            // Pre-load history for the newly selected active session
            fetchSessionHistory(filtered[0].id)
              .then(data => {
                setAllMessages(prevAll => ({
                  ...prevAll,
                  [filtered[0].id]: data.messages || []
                }));
              })
              .catch(e => console.error(e));
          } else {
            const newId = generateSessionId();
            setSessionId(newId);
            setAllMessages({ [newId]: [] });
            return [{ id: newId, name: 'New Conversation' }];
          }
        }
        return filtered;
      });

      setAllMessages(prev => {
        const copy = { ...prev };
        delete copy[id];
        return copy;
      });
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const handleClearSessions = async () => {
    try {
      // Loop through and delete all sessions
      for (const s of sessions) {
        try {
          await deleteSession(s.id);
        } catch (e) {
          // ignore error
        }
      }
    } catch (err) {
      console.error("Failed to clear sessions:", err);
    }
    
    const newId = generateSessionId();
    setSessionId(newId);
    setSessions([{ id: newId, name: 'New Conversation' }]);
    setAllMessages({ [newId]: [] });
    setMobileMenuOpen(false);
  };

  const handleSendMessage = async (text) => {
    if (!text.trim() || isLoading) return;

    const userMsg = { 
      role: 'user', 
      content: text,
      created_at: new Date().toISOString()
    };
    const currentMsgs = allMessages[sessionId] || [];
    
    // Add placeholder assistant message that will be populated via SSE stream
    const assistantMsg = { 
      role: 'assistant', 
      content: '', 
      sources: [],
      created_at: new Date().toISOString()
    };
    
    setAllMessages(prev => ({
      ...prev,
      [sessionId]: [...currentMsgs, userMsg, assistantMsg]
    }));
    
    setIsLoading(true);

    let streamAnswer = "";
    let streamSources = [];

    const updateAssistantState = (newAnswer, newSources) => {
      setAllMessages(prev => {
        const list = prev[sessionId] || [];
        if (list.length === 0) return prev;
        const updatedList = [...list];
        updatedList[updatedList.length - 1] = {
          ...updatedList[updatedList.length - 1],
          content: newAnswer,
          sources: newSources
        };
        return {
          ...prev,
          [sessionId]: updatedList
        };
      });
    };

    try {
      await queryStream(
        text,
        sessionId,
        (token) => {
          streamAnswer += token;
          updateAssistantState(streamAnswer, streamSources);
        },
        (sources) => {
          streamSources = sources;
          updateAssistantState(streamAnswer, streamSources);
        },
        (error) => {
          console.error("Query stream error:", error);
          const errDetail = error.message || "Failed to receive streaming response. Backend offline or rate limited.";
          streamAnswer += `\n[Stream Error: ${errDetail}]`;
          updateAssistantState(streamAnswer, streamSources);
          setIsLoading(false);
        },
        () => {
          setIsLoading(false);
          // Auto-rename session name dynamically from first query
          setSessions(prev => prev.map(s => {
            if (s.id === sessionId && (s.name === 'New Conversation' || s.name === 'General Document Query')) {
              return { ...s, name: text.length > 25 ? `${text.substring(0, 22)}...` : text };
            }
            return s;
          }));
        }
      );
    } catch (err) {
      console.error(err);
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('rag_token');
    setIsAuthenticated(false);
    setView('login');
    setSessionId('');
    setSessions([]);
    setAllMessages({});
    setActiveDocument(null);
  };

  // Switch layouts based on view state
  if (view === 'login') {
    return (
      <Login 
        onLoginSuccess={() => {
          setIsAuthenticated(true);
          setView('chat');
        }}
        onNavigateToSignup={() => setView('register')}
      />
    );
  }

  if (view === 'register') {
    return (
      <Register
        onSignupSuccess={() => setView('login')}
        onNavigateToLogin={() => setView('login')}
      />
    );
  }

  if (view === 'dashboard') {
    return (
      <Dashboard 
        onBackToChat={() => setView('chat')}
      />
    );
  }

  const currentMessages = allMessages[sessionId] || [];

  return (
    <div className="flex h-screen bg-[#212121] text-gray-200 overflow-hidden font-sans select-none">
      
      {/* Desktop Sidebar Panel */}
      <div className="hidden md:flex h-full shrink-0">
        <Sidebar
          sessionId={sessionId}
          sessions={sessions}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
          onNewChat={handleNewChat}
          onClearSessions={handleClearSessions}
          activeDocument={activeDocument}
          setActiveDocument={setActiveDocument}
          onLogout={handleLogout}
          onOpenDashboard={() => setView('dashboard')}
        />
      </div>

      {/* Mobile Sidebar Navigation Hamburger Toggles */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        <header className="md:hidden h-14 bg-[#171717] border-b border-[#2f2f2f] px-4 flex items-center justify-between shrink-0">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <Menu className="w-6 h-6" />
          </button>
          
          <div className="flex items-center space-x-1.5">
            <Database className="w-5 h-5 text-emerald-500" />
            <span className="font-semibold text-sm">DocSearch RAG</span>
          </div>
          
          <div className="w-6" /> {/* Spacer */}
        </header>

        {/* Chat Window Panel */}
        <ChatWindow
          messages={currentMessages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          activeDocument={activeDocument}
        />
      </div>

      {/* Mobile Sidebar Overlay Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden bg-black/60 backdrop-blur-sm">
          <div className="relative w-80 h-full flex flex-col animate-fade-in">
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors z-50"
            >
              <X className="w-5 h-5" />
            </button>
            <Sidebar
              sessionId={sessionId}
              sessions={sessions}
              onSelectSession={handleSelectSession}
              onDeleteSession={handleDeleteSession}
              onNewChat={handleNewChat}
              onClearSessions={handleClearSessions}
              activeDocument={activeDocument}
              setActiveDocument={setActiveDocument}
              onLogout={handleLogout}
              onOpenDashboard={() => setView('dashboard')}
            />
          </div>
          <div className="flex-1" onClick={() => setMobileMenuOpen(false)} />
        </div>
      )}

    </div>
  );
}
