import React, { useState, useRef, useEffect } from 'react';
import { 
  Plus, 
  MessageSquare, 
  UploadCloud, 
  CheckCircle2, 
  AlertCircle, 
  Trash2, 
  Loader2, 
  Database,
  FileText,
  LogOut,
  BarChart3,
  X
} from 'lucide-react';
import { uploadDocument, checkHealth } from '../api';

export default function Sidebar({ 
  sessionId, 
  sessions, 
  onSelectSession, 
  onDeleteSession,
  onNewChat, 
  onClearSessions,
  activeDocument,
  setActiveDocument,
  onLogout,
  onOpenDashboard
}) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [uploadState, setUploadState] = useState('idle'); // 'idle' | 'uploading' | 'success' | 'error'
  const [errorMessage, setErrorMessage] = useState('');
  const [chunkCount, setChunkCount] = useState(null);
  const [backendStatus, setBackendStatus] = useState('connecting'); // 'connecting' | 'online' | 'offline'
  const fileInputRef = useRef(null);

  // Check health of backend on load
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        await checkHealth();
        setBackendStatus('online');
      } catch (err) {
        setBackendStatus('offline');
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const getExtension = (filename) => {
    return filename.split('.').pop().toLowerCase();
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      const ext = getExtension(droppedFile.name);
      if (['pdf', 'docx', 'txt'].includes(ext)) {
        setFile(droppedFile);
        setUploadState('idle');
      } else {
        setErrorMessage("Only PDF, DOCX, and TXT files are supported");
        setUploadState('error');
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      const ext = getExtension(selectedFile.name);
      if (['pdf', 'docx', 'txt'].includes(ext)) {
        setFile(selectedFile);
        setUploadState('idle');
      } else {
        setErrorMessage("Only PDF, DOCX, and TXT files are supported");
        setUploadState('error');
      }
    }
  };

  const onButtonClick = () => {
    fileInputRef.current.click();
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploadState('uploading');
    setErrorMessage('');
    
    try {
      const data = await uploadDocument(file);
      setUploadState('success');
      setChunkCount(data.total_chunks);
      setActiveDocument({
        name: file.name,
        chunks: data.total_chunks
      });
      setFile(null);
    } catch (error) {
      console.error(error);
      const detail = error.response?.data?.detail || "Upload ingestion failed. Verify API key configurations.";
      setErrorMessage(detail);
      setUploadState('error');
    }
  };

  return (
    <div className="w-full md:w-80 bg-[#171717] flex flex-col h-full text-gray-200 border-r border-[#2f2f2f] shrink-0 font-sans">
      
      {/* Brand Header */}
      <div className="p-4 border-b border-[#2f2f2f] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Database className="w-6 h-6 text-emerald-500" />
          <span className="font-semibold text-base tracking-wide bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            AI Document Assistant
          </span>
        </div>
        <div className="flex items-center space-x-1">
          <span className={`w-2.5 h-2.5 rounded-full ${
            backendStatus === 'online' ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' : 
            backendStatus === 'offline' ? 'bg-rose-500 shadow-[0_0_8px_#f43f5e]' : 
            'bg-amber-500 animate-pulse'
          }`} />
          <span className="text-[9px] text-gray-400 uppercase tracking-wider font-mono">
            {backendStatus}
          </span>
        </div>
      </div>

      {/* Primary Action Panel */}
      <div className="p-4 flex flex-col space-y-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 transition-colors rounded-xl text-white font-semibold text-xs shadow-[0_2px_10px_rgba(16,185,129,0.15)] focus:outline-none"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat Session</span>
        </button>
        <button
          onClick={onOpenDashboard}
          className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-[#2f2f2f] hover:bg-[#383838] transition-colors border border-[#3d3d3d] rounded-xl text-gray-200 font-semibold text-xs focus:outline-none"
        >
          <BarChart3 className="w-4 h-4 text-emerald-400" />
          <span>Admin Stats Dashboard</span>
        </button>
      </div>

      {/* Document Ingestion Widget */}
      <div className="px-4 pb-4 border-b border-[#2f2f2f]">
        <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
          Ingest Document (PDF, DOCX, TXT)
        </label>
        
        <div 
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={uploadState !== 'uploading' ? onButtonClick : null}
          className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all duration-200 ${
            dragActive 
              ? 'border-emerald-500 bg-emerald-950/20' 
              : 'border-[#424242] bg-[#212121] hover:border-gray-500'
          }`}
        >
          <input 
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
            className="hidden"
            disabled={uploadState === 'uploading'}
          />
          
          <UploadCloud className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-xs text-gray-300 font-medium">
            Drag & drop here, or <span className="text-emerald-400 hover:underline">browse</span>
          </p>
          <p className="text-[10px] text-gray-500 mt-1">PDF, DOCX, TXT files up to 20MB</p>
        </div>

        {/* Selected File Details */}
        {file && uploadState !== 'success' && (
          <div className="mt-3 bg-[#212121] p-3 rounded-xl flex flex-col space-y-2 border border-[#2f2f2f]">
            <div className="flex items-center space-x-2 text-xs">
              <FileText className="w-4 h-4 text-emerald-400 shrink-0" />
              <span className="truncate font-medium text-gray-300 max-w-[160px]">{file.name}</span>
            </div>
            
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleUpload();
              }}
              disabled={uploadState === 'uploading'}
              className="w-full py-1.5 px-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors"
            >
              {uploadState === 'uploading' ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Ingesting file...</span>
                </>
              ) : (
                <span>Ingest Document</span>
              )}
            </button>
          </div>
        )}

        {/* Alerts */}
        {uploadState === 'success' && (
          <div className="mt-3 bg-emerald-950/20 border border-emerald-800/50 p-2.5 rounded-xl flex items-start space-x-2 text-xs text-emerald-400">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Ingested successfully!</p>
              <p className="text-[10px] text-emerald-500/80 mt-0.5">{chunkCount} chunks generated.</p>
            </div>
          </div>
        )}

        {uploadState === 'error' && (
          <div className="mt-3 bg-rose-950/20 border border-rose-800/50 p-2.5 rounded-xl flex items-start space-x-2 text-xs text-rose-400">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="truncate max-w-[200px]">
              <p className="font-semibold">Ingestion failed</p>
              <p className="text-[10px] text-rose-500/80 mt-0.5 truncate">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Active Context file */}
        {activeDocument && (
          <div className="mt-3 bg-[#262626] p-2.5 rounded-xl border border-[#363636] flex items-center justify-between text-xs text-gray-300">
            <div className="flex items-center space-x-2 truncate">
              <FileText className="w-4 h-4 text-emerald-400 shrink-0" />
              <div className="truncate">
                <p className="font-medium truncate max-w-[130px]">{activeDocument.name}</p>
                <p className="text-[10px] text-gray-500">{activeDocument.chunks} chunks active</p>
              </div>
            </div>
            <button 
              onClick={() => setActiveDocument(null)}
              className="text-gray-500 hover:text-rose-400 transition-colors"
              title="Deactivate Document Context"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Chat History Sessions */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1.5">
        <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
          Chat Session History
        </label>
        
        {sessions.length === 0 ? (
          <div className="text-center py-6 text-xs text-gray-500 italic">
            No active conversations
          </div>
        ) : (
          sessions.map((sess) => (
            <div
              key={sess.id}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs transition-all duration-150 group cursor-pointer ${
                sessionId === sess.id 
                  ? 'bg-[#2f2f2f] text-white font-medium shadow-sm' 
                  : 'hover:bg-[#212121] text-gray-400 hover:text-gray-200'
              }`}
              onClick={() => onSelectSession(sess.id)}
            >
              <div className="flex items-center space-x-3 truncate flex-1 mr-2">
                <MessageSquare className="w-4 h-4 shrink-0 text-gray-400 group-hover:text-emerald-400" />
                <span className="truncate">{sess.name}</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation(); // Stop click propagating to session selector
                  onDeleteSession(sess.id);
                }}
                className="opacity-0 group-hover:opacity-100 hover:text-rose-400 text-gray-500 transition-all focus:outline-none"
                title="Delete Session"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Footer Clear and Logout Panel */}
      <div className="p-4 border-t border-[#2f2f2f] flex flex-col space-y-2">
        {sessions.length > 0 && (
          <button
            onClick={onClearSessions}
            className="w-full flex items-center justify-center space-x-2 py-2 px-3 hover:bg-rose-950/20 border border-[#333] hover:border-rose-900/50 text-gray-400 hover:text-rose-400 rounded-xl text-xs font-semibold transition-all focus:outline-none"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear History</span>
          </button>
        )}
        <button
          onClick={onLogout}
          className="w-full flex items-center justify-center space-x-2 py-2 px-3 hover:bg-zinc-800 border border-[#333] hover:border-zinc-700 text-gray-400 hover:text-white rounded-xl text-xs font-semibold transition-all focus:outline-none"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
}
