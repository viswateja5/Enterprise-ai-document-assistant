import React, { useState } from 'react';
import { Database, Loader2, UserPlus } from 'lucide-react';
import { signupUser } from '../api';

export default function Register({ onSignupSuccess, onNavigateToLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) return;
    
    if (username.length < 3) {
      setError("Username must be at least 3 characters long");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters long");
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      await signupUser(username, password);
      setSuccess(true);
      setTimeout(() => {
        onSignupSuccess();
      }, 1500);
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.detail || "Registration failed. Username may already be taken.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#212121] flex flex-col justify-center items-center px-4 font-sans selection:bg-emerald-800">
      <div className="w-full max-w-md bg-[#171717] border border-[#2f2f2f] rounded-2xl p-8 shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
        {/* Brand Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-emerald-950/40 border border-emerald-800/30 rounded-full flex items-center justify-center mb-3">
            <Database className="w-6 h-6 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-gray-100">Create Account</h1>
          <p className="text-xs text-gray-500 mt-1">Register for AI Document Search</p>
        </div>

        {error && (
          <div className="mb-4 bg-rose-950/20 border border-rose-900/50 p-3 rounded-lg text-xs text-rose-400 font-medium text-center">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 bg-emerald-950/20 border border-emerald-900/50 p-3 rounded-lg text-xs text-emerald-400 font-medium text-center">
            Registration successful! Redirecting to login...
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Min 3 characters"
              className="w-full py-2.5 px-4 rounded-lg bg-[#212121] border border-[#3c3c3c] text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-emerald-600 transition-colors"
              disabled={loading || success}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min 6 characters"
              className="w-full py-2.5 px-4 rounded-lg bg-[#212121] border border-[#3c3c3c] text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-emerald-600 transition-colors"
              disabled={loading || success}
            />
          </div>

          <button
            type="submit"
            disabled={loading || success}
            className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-semibold flex items-center justify-center space-x-2 transition-colors focus:outline-none shadow-md mt-6"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Creating Account...</span>
              </>
            ) : (
              <>
                <UserPlus className="w-4 h-4" />
                <span>Sign Up</span>
              </>
            )}
          </button>
        </form>

        <div className="mt-6 text-center text-xs text-gray-500">
          Already have an account?{' '}
          <button 
            onClick={onNavigateToLogin}
            className="text-emerald-400 hover:underline font-medium focus:outline-none"
            disabled={loading || success}
          >
            Log in here
          </button>
        </div>
      </div>
    </div>
  );
}
