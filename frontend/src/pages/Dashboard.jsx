import React, { useState, useEffect } from 'react';
import { 
  Users, 
  MessageSquare, 
  FileText, 
  Database, 
  Zap, 
  Clock, 
  ArrowLeft, 
  RefreshCw,
  TrendingUp,
  Activity,
  Server
} from 'lucide-react';
import { fetchAdminStats } from '../api';

export default function Dashboard({ onBackToChat }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadStats = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchAdminStats();
      setStats(data);
    } catch (err) {
      console.error(err);
      setError("Failed to load dashboard analytics statistics. Verify authorization or server connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const cacheHitRatio = stats 
    ? (stats.cache_hits / (stats.query_count || 1)) * 100 
    : 0;

  return (
    <div className="min-h-screen bg-[#212121] text-gray-200 p-6 md:p-10 font-sans select-none overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 mb-8 border-b border-[#2f2f2f] pb-6">
          <div>
            <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-xs uppercase tracking-widest mb-1.5">
              <Server className="w-4 h-4" />
              <span>Admin Monitoring Console</span>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">System Performance & Stats</h1>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={loadStats}
              disabled={loading}
              className="p-2.5 rounded-xl bg-[#2f2f2f] hover:bg-[#383838] border border-[#3c3c3c] text-gray-300 hover:text-white transition-all duration-150 focus:outline-none flex items-center justify-center disabled:opacity-40"
              title="Refresh Analytics"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onBackToChat}
              className="flex items-center space-x-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-semibold transition-all shadow-md focus:outline-none"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Chat</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-rose-950/20 border border-rose-900/50 p-4 rounded-xl text-sm text-rose-400 font-medium">
            {error}
          </div>
        )}

        {loading && !stats ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400 space-y-3">
            <RefreshCw className="w-10 h-10 animate-spin text-emerald-500" />
            <p className="text-sm font-medium animate-pulse">Fetching system performance metrics...</p>
          </div>
        ) : (
          stats && (
            <div className="space-y-8">
              
              {/* Analytics Core Cards Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                
                {/* User registration count */}
                <div className="bg-[#171717] border border-[#2f2f2f] p-6 rounded-2xl flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-xl bg-blue-950/40 border border-blue-900/30 flex items-center justify-center text-blue-400 shrink-0">
                    <Users className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total User Accounts</p>
                    <h2 className="text-3xl font-extrabold text-white mt-1">{stats.total_users}</h2>
                  </div>
                </div>

                {/* Chat session count */}
                <div className="bg-[#171717] border border-[#2f2f2f] p-6 rounded-2xl flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-xl bg-purple-950/40 border border-purple-900/30 flex items-center justify-center text-purple-400 shrink-0">
                    <MessageSquare className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Chat Sessions</p>
                    <h2 className="text-3xl font-extrabold text-white mt-1">{stats.total_chats}</h2>
                  </div>
                </div>

                {/* Uploaded documents count */}
                <div className="bg-[#171717] border border-[#2f2f2f] p-6 rounded-2xl flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-xl bg-emerald-950/40 border border-emerald-800/30 flex items-center justify-center text-emerald-400 shrink-0">
                    <FileText className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Uploaded Documents</p>
                    <h2 className="text-3xl font-extrabold text-white mt-1">{stats.uploaded_documents}</h2>
                  </div>
                </div>

                {/* Total chunk count */}
                <div className="bg-[#171717] border border-[#2f2f2f] p-6 rounded-2xl flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-xl bg-amber-950/40 border border-amber-900/30 flex items-center justify-center text-amber-400 shrink-0">
                    <Database className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Vector DB Chunks</p>
                    <h2 className="text-3xl font-extrabold text-white mt-1">{stats.number_of_chunks}</h2>
                  </div>
                </div>

                {/* Query execution count */}
                <div className="bg-[#171717] border border-[#2f2f2f] p-6 rounded-2xl flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-xl bg-pink-950/40 border border-pink-900/30 flex items-center justify-center text-pink-400 shrink-0">
                    <Activity className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">RAG Query Executions</p>
                    <h2 className="text-3xl font-extrabold text-white mt-1">{stats.query_count}</h2>
                  </div>
                </div>

                {/* Average response latency */}
                <div className="bg-[#171717] border border-[#2f2f2f] p-6 rounded-2xl flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-xl bg-rose-950/40 border border-rose-900/30 flex items-center justify-center text-rose-400 shrink-0">
                    <Clock className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Average Latency</p>
                    <h2 className="text-3xl font-extrabold text-white mt-1">
                      {stats.average_response_time > 0 ? `${stats.average_response_time.toFixed(3)}s` : "0.00s"}
                    </h2>
                  </div>
                </div>

              </div>

              {/* Cache Efficiency Segment */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                
                {/* Cache Hits Card info */}
                <div className="bg-[#171717] border border-[#2f2f2f] p-6 rounded-2xl flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-white">Cache Performance</h3>
                      <p className="text-xs text-gray-500">Query caching hit distributions (Redis vs LLM)</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-orange-950/40 border border-orange-900/30 flex items-center justify-center text-orange-400 shrink-0">
                      <Zap className="w-5 h-5" />
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex justify-between items-end">
                      <span className="text-xs text-gray-400">Total Cache Hits:</span>
                      <span className="text-xl font-bold text-emerald-400">{stats.cache_hits}</span>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs text-gray-500 mb-1">
                        <span>Cache Hit Ratio</span>
                        <span>{cacheHitRatio.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-[#2f2f2f] rounded-full h-3 overflow-hidden">
                        <div 
                          className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full transition-all duration-500" 
                          style={{ width: `${Math.min(cacheHitRatio, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* System Diagnostics Stats */}
                <div className="bg-[#171717] border border-[#2f2f2f] p-6 rounded-2xl flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-white">RAG Index Health</h3>
                      <p className="text-xs text-gray-500">Vector store density diagnostics</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-emerald-950/40 border border-emerald-900/30 flex items-center justify-center text-emerald-400 shrink-0">
                      <TrendingUp className="w-5 h-5" />
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex justify-between text-xs text-gray-400">
                      <span>Index Type:</span>
                      <span className="font-semibold text-gray-200">FAISS Index (CPU)</span>
                    </div>
                    <div className="flex justify-between text-xs text-gray-400">
                      <span>Average Chunks / PDF:</span>
                      <span className="font-semibold text-gray-200">
                        {stats.uploaded_documents > 0 
                          ? (stats.number_of_chunks / stats.uploaded_documents).toFixed(1) 
                          : "0.0"}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs text-gray-400">
                      <span>Cache Status:</span>
                      <span className="font-semibold text-emerald-400">Cache Active</span>
                    </div>
                  </div>
                </div>

              </div>

            </div>
          )
        )}

      </div>
    </div>
  );
}
