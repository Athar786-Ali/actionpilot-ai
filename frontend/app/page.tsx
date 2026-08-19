'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bot,
  Rocket,
  Terminal,
  Shield,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Pause,
  Send,
  Zap,
  Eye,
  ChevronRight,
  Sparkles,
  Globe,
  Lock,
  X,
} from 'lucide-react';
import { createJob, getJob, submitOtp } from '@/lib/api';
import type { Job, AuditLog, JobStatus } from '@/lib/types';

// ═══════════════════════════════════════════════════════════════
// STATUS BADGE COMPONENT
// ═══════════════════════════════════════════════════════════════

function StatusBadge({ status }: { status: JobStatus }) {
  const config: Record<
    JobStatus,
    { label: string; color: string; bg: string; icon: React.ReactNode; pulse: boolean }
  > = {
    PENDING: {
      label: 'Pending',
      color: 'text-yellow-400',
      bg: 'bg-yellow-400/10 border-yellow-400/30',
      icon: <Clock className="w-3.5 h-3.5" />,
      pulse: true,
    },
    RUNNING: {
      label: 'Running',
      color: 'text-blue-400',
      bg: 'bg-blue-400/10 border-blue-400/30',
      icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
      pulse: false,
    },
    PAUSED_FOR_HITL: {
      label: 'Awaiting Human',
      color: 'text-orange-400',
      bg: 'bg-orange-400/10 border-orange-400/30',
      icon: <Pause className="w-3.5 h-3.5" />,
      pulse: true,
    },
    COMPLETED: {
      label: 'Completed',
      color: 'text-emerald-400',
      bg: 'bg-emerald-400/10 border-emerald-400/30',
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      pulse: false,
    },
    FAILED: {
      label: 'Failed',
      color: 'text-red-400',
      bg: 'bg-red-400/10 border-red-400/30',
      icon: <XCircle className="w-3.5 h-3.5" />,
      pulse: false,
    },
  };

  const c = config[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${c.bg} ${c.color} transition-all duration-300`}
    >
      {c.icon}
      {c.label}
      {c.pulse && (
        <span className="relative flex h-2 w-2">
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${c.color.replace('text-', 'bg-')}`}
          />
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${c.color.replace('text-', 'bg-')}`}
          />
        </span>
      )}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════
// LOG ENTRY COMPONENT
// ═══════════════════════════════════════════════════════════════

function LogEntry({ log, index }: { log: AuditLog; index: number }) {
  const actionColors: Record<string, string> = {
    JOB_STARTED: 'text-blue-400',
    JOB_COMPLETED: 'text-emerald-400',
    JOB_FAILED: 'text-red-400',
    AGENT_INITIALIZED: 'text-indigo-400',
    AGENT_ACTION: 'text-cyan-400',
    AGENT_GOAL: 'text-violet-400',
    HITL_REQUESTED: 'text-orange-400',
    HITL_RESUMED: 'text-amber-400',
    HITL_OTP_SUBMITTED: 'text-green-400',
    NAVIGATE: 'text-cyan-400',
    CLICK: 'text-sky-400',
    TYPE: 'text-teal-400',
    SCROLL: 'text-indigo-300',
    DONE: 'text-emerald-400',
  };

  const color = actionColors[log.actionType] || 'text-zinc-400';
  const time = new Date(log.timestamp).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <div
      className="flex items-start gap-3 py-2 px-3 rounded-lg hover:bg-white/[0.02] transition-colors duration-200 group"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Timeline dot */}
      <div className="flex flex-col items-center pt-1.5 shrink-0">
        <div className={`w-2 h-2 rounded-full ${color.replace('text-', 'bg-')} shadow-[0_0_8px] ${color.replace('text-', 'shadow-')}/50`} />
        {/* Connecting line */}
        <div className="w-px h-full bg-zinc-800 mt-1" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={`text-xs font-mono font-bold ${color}`}>
            [{log.actionType}]
          </span>
          <span className="text-[10px] text-zinc-600 font-mono">{time}</span>
        </div>
        <p className="text-sm text-zinc-300 leading-relaxed break-words">
          {log.description}
        </p>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// HITL MODAL COMPONENT
// ═══════════════════════════════════════════════════════════════

function HITLModal({
  isOpen,
  jobId,
  onClose,
}: {
  isOpen: boolean;
  jobId: string;
  onClose: () => void;
}) {
  const [otp, setOtp] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setOtp('');
      setError('');
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSubmit = async () => {
    if (!otp.trim()) {
      setError('Please enter the OTP/verification code');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const res = await submitOtp(jobId, otp.trim());
      if (res.success) {
        onClose();
      } else {
        setError(res.error || 'Failed to submit OTP');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md glass-strong rounded-2xl p-6 shadow-2xl shadow-orange-500/10 animate-in fade-in zoom-in duration-300">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Glowing alert icon */}
        <div className="flex justify-center mb-5">
          <div className="relative">
            <div className="absolute inset-0 bg-orange-500/30 rounded-full blur-xl animate-pulse" />
            <div className="relative bg-orange-500/10 border border-orange-500/30 rounded-full p-4">
              <Shield className="w-8 h-8 text-orange-400" />
            </div>
          </div>
        </div>

        <h3 className="text-xl font-bold text-center mb-2">
          Human Verification Required
        </h3>
        <p className="text-sm text-zinc-400 text-center mb-6">
          The agent has paused and is waiting for an OTP or verification code.
          Please check your device and enter the code below.
        </p>

        {/* OTP Input */}
        <div className="space-y-3">
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              ref={inputRef}
              type="text"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="Enter OTP / verification code"
              maxLength={20}
              className="w-full pl-10 pr-4 py-3 bg-zinc-900/80 border border-zinc-700 rounded-xl text-center text-lg font-mono tracking-[0.3em] text-white placeholder:text-zinc-600 placeholder:tracking-normal placeholder:text-sm focus:outline-none focus:border-orange-500/50 focus:ring-2 focus:ring-orange-500/20 transition-all duration-200"
            />
          </div>

          {error && (
            <p className="text-xs text-red-400 text-center">{error}</p>
          )}

          <button
            onClick={handleSubmit}
            disabled={submitting || !otp.trim()}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-400 hover:to-amber-400 disabled:from-zinc-700 disabled:to-zinc-700 disabled:text-zinc-500 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-orange-500/25 hover:shadow-orange-500/40 disabled:shadow-none"
          >
            {submitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            {submitting ? 'Submitting...' : 'Submit & Resume Agent'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═══════════════════════════════════════════════════════════════

export default function Home() {
  // ── State ─────────────────────────────────────────────────────
  const [prompt, setPrompt] = useState('');
  const [launching, setLaunching] = useState(false);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [showHITL, setShowHITL] = useState(false);
  const [error, setError] = useState('');

  const logsEndRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Auto-scroll logs ──────────────────────────────────────────
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // ── Polling logic ─────────────────────────────────────────────
  const startPolling = useCallback((jobId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);

    const poll = async () => {
      try {
        const res = await getJob(jobId);
        if (!res.success || !res.data) return;

        const job = res.data;
        setActiveJob(job);
        setLogs(job.auditLogs || []);

        // Trigger HITL modal
        if (job.status === 'PAUSED_FOR_HITL') {
          setShowHITL(true);
        } else {
          setShowHITL(false);
        }

        // Stop polling on terminal states
        if (job.status === 'COMPLETED' || job.status === 'FAILED') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        }
      } catch {
        // Silently retry on network errors
      }
    };

    // Immediate first poll
    poll();
    pollingRef.current = setInterval(poll, 2000);
  }, []);

  // ── Cleanup on unmount ────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  // ── Launch agent ──────────────────────────────────────────────
  const handleLaunch = async () => {
    if (!prompt.trim()) return;
    setLaunching(true);
    setError('');
    setLogs([]);
    setActiveJob(null);

    try {
      const res = await createJob(prompt.trim());
      if (res.success && res.data) {
        setActiveJob(res.data);
        startPolling(res.data.id);
        setPrompt('');
      } else {
        setError(res.error || 'Failed to create job');
      }
    } catch {
      setError('Could not connect to the API. Is the backend running?');
    } finally {
      setLaunching(false);
    }
  };

  // ── Terminal status helpers ───────────────────────────────────
  const isTerminal =
    activeJob?.status === 'COMPLETED' || activeJob?.status === 'FAILED';
  const isActive = activeJob && !isTerminal;

  // ═════════════════════════════════════════════════════════════
  // RENDER
  // ═════════════════════════════════════════════════════════════
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* ── Ambient background glow ───────────────────────────── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-[40%] -left-[20%] w-[70%] h-[70%] rounded-full bg-indigo-600/[0.07] blur-[120px]" />
        <div className="absolute -bottom-[30%] -right-[20%] w-[60%] h-[60%] rounded-full bg-cyan-500/[0.05] blur-[120px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[40%] h-[40%] rounded-full bg-violet-600/[0.04] blur-[100px]" />
      </div>

      {/* ── Grid pattern overlay ──────────────────────────────── */}
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />

      <div className="relative z-10 max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* ═══════════════════════════════════════════════════════
            HERO HEADER
        ═══════════════════════════════════════════════════════ */}
        <header className="text-center mb-12 pt-8">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-xs font-medium text-zinc-300 mb-6 animate-float">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            Agentic Workflow Active
          </div>

          {/* Title */}
          <h1 className="text-5xl sm:text-6xl font-black tracking-tight mb-4">
            <span className="bg-gradient-to-r from-indigo-400 via-cyan-400 to-indigo-400 bg-clip-text text-transparent">
              ActionPilot
            </span>{' '}
            <span className="text-white">AI</span>
          </h1>

          {/* Glow line under title */}
          <div className="mx-auto w-32 h-1 rounded-full bg-gradient-to-r from-transparent via-indigo-500 to-transparent mb-4 animate-glow-pulse" />

          <p className="text-zinc-400 text-lg max-w-xl mx-auto">
            Autonomous browser automation powered by{' '}
            <span className="text-cyan-400 font-medium">Gemini AI</span>.
            Describe any web task — the agent navigates, clicks, and types for
            you.
          </p>

          {/* Feature pills */}
          <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
            {[
              { icon: <Bot className="w-3.5 h-3.5" />, text: 'LLM-Powered' },
              {
                icon: <Eye className="w-3.5 h-3.5" />,
                text: 'Vision-Capable',
              },
              {
                icon: <Globe className="w-3.5 h-3.5" />,
                text: 'Real Browser',
              },
              {
                icon: <Shield className="w-3.5 h-3.5" />,
                text: 'Human-in-the-Loop',
              },
            ].map((f) => (
              <span
                key={f.text}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs text-zinc-400 border border-zinc-800 bg-zinc-900/50"
              >
                {f.icon}
                {f.text}
              </span>
            ))}
          </div>
        </header>

        {/* ═══════════════════════════════════════════════════════
            COMMAND CENTER
        ═══════════════════════════════════════════════════════ */}
        <section className="mb-8">
          <div className="glass rounded-2xl p-6 shadow-lg shadow-indigo-500/5">
            {/* Input label */}
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-semibold text-zinc-300">
                Mission Prompt
              </span>
            </div>

            {/* Textarea */}
            <div className="relative mb-4">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleLaunch();
                  }
                }}
                placeholder="Describe your web task... e.g. &quot;Go to amazon.in, search for wireless headphones, and extract the top 5 results with prices&quot;"
                rows={3}
                disabled={launching}
                className="w-full px-4 py-3 bg-zinc-900/60 border border-zinc-700/50 rounded-xl text-white placeholder:text-zinc-600 resize-none focus:outline-none focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 transition-all duration-200 text-sm leading-relaxed disabled:opacity-50"
              />
              {/* Glow border effect on focus */}
              <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-indigo-500/0 via-indigo-500/0 to-cyan-500/0 opacity-0 focus-within:opacity-100 transition-opacity duration-500 pointer-events-none -z-10 blur-sm" />
            </div>

            {/* Action bar */}
            <div className="flex items-center justify-between gap-4">
              <p className="text-xs text-zinc-600">
                Press{' '}
                <kbd className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 text-[10px] font-mono border border-zinc-700">
                  Enter
                </kbd>{' '}
                to launch · Shift+Enter for new line
              </p>

              <button
                onClick={handleLaunch}
                disabled={launching || !prompt.trim()}
                className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:from-zinc-700 disabled:to-zinc-700 disabled:text-zinc-500 text-white font-semibold rounded-xl text-sm transition-all duration-200 shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 disabled:shadow-none hover:scale-[1.02] active:scale-[0.98]"
              >
                {launching ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Rocket className="w-4 h-4" />
                )}
                {launching ? 'Launching...' : 'Launch Agent'}
              </button>
            </div>

            {error && (
              <div className="mt-3 flex items-center gap-2 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
                <XCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════
            LIVE EXECUTION CONSOLE
        ═══════════════════════════════════════════════════════ */}
        {activeJob && (
          <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="glass rounded-2xl overflow-hidden shadow-lg shadow-black/20">
              {/* Console header */}
              <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800/80 bg-zinc-900/50">
                <div className="flex items-center gap-3">
                  {/* macOS dots */}
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/80" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                    <div className="w-3 h-3 rounded-full bg-green-500/80" />
                  </div>

                  <div className="flex items-center gap-2 pl-2">
                    <Terminal className="w-4 h-4 text-zinc-500" />
                    <span className="text-xs font-mono text-zinc-400">
                      live-execution-console
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {isActive && (
                    <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-wider">
                      Polling every 2s
                    </span>
                  )}
                  <StatusBadge status={activeJob.status} />
                </div>
              </div>

              {/* Job info bar */}
              <div className="px-5 py-2.5 border-b border-zinc-800/50 bg-zinc-900/30">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-zinc-600 font-mono">JOB</span>
                  <code className="text-indigo-400 font-mono">
                    {activeJob.id.slice(0, 8)}...
                  </code>
                  <ChevronRight className="w-3 h-3 text-zinc-700" />
                  <span className="text-zinc-400 truncate max-w-md">
                    {activeJob.prompt}
                  </span>
                </div>
              </div>

              {/* Logs area */}
              <div className="max-h-[440px] overflow-y-auto p-4 space-y-0.5">
                {logs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-zinc-600">
                    <Loader2 className="w-6 h-6 animate-spin mb-3 text-zinc-700" />
                    <span className="text-sm">
                      Waiting for agent actions...
                    </span>
                  </div>
                ) : (
                  logs.map((log, i) => (
                    <LogEntry key={log.id} log={log} index={i} />
                  ))
                )}
                <div ref={logsEndRef} />
              </div>

              {/* Console footer */}
              <div className="px-5 py-2.5 border-t border-zinc-800/80 bg-zinc-900/50 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-zinc-600 font-mono">
                  <Zap className="w-3 h-3" />
                  {logs.length} action{logs.length !== 1 ? 's' : ''} logged
                </div>
                {isActive && (
                  <div className="flex items-center gap-1.5 text-xs text-zinc-600">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Live
                  </div>
                )}
                {activeJob.status === 'COMPLETED' && (
                  <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Mission Complete
                  </span>
                )}
                {activeJob.status === 'FAILED' && (
                  <span className="text-xs text-red-400 font-medium flex items-center gap-1">
                    <XCircle className="w-3.5 h-3.5" />
                    Mission Failed
                  </span>
                )}
              </div>
            </div>

            {/* Result card (shown on completion) */}
            {activeJob.status === 'COMPLETED' && Boolean(activeJob.resultData) && (
              <div className="mt-4 glass rounded-2xl p-5 animate-in fade-in slide-in-from-bottom-2 duration-500">
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm font-semibold text-emerald-400">
                    Agent Result
                  </span>
                </div>
                <pre className="text-xs text-zinc-300 bg-zinc-900/50 rounded-lg p-4 overflow-x-auto font-mono leading-relaxed whitespace-pre-wrap">
                  {typeof activeJob.resultData === 'string'
                    ? (activeJob.resultData as string)
                    : JSON.stringify(activeJob.resultData as object, null, 2)}
                </pre>
              </div>
            )}

            {/* Launch another */}
            {isTerminal && (
              <div className="mt-4 text-center">
                <button
                  onClick={() => {
                    setActiveJob(null);
                    setLogs([]);
                    setError('');
                  }}
                  className="inline-flex items-center gap-2 px-5 py-2 text-sm text-zinc-400 hover:text-white border border-zinc-800 hover:border-zinc-600 rounded-xl transition-all duration-200 hover:bg-zinc-800/50"
                >
                  <Rocket className="w-4 h-4" />
                  Launch Another Mission
                </button>
              </div>
            )}
          </section>
        )}

        {/* ── Footer ──────────────────────────────────────────── */}
        <footer className="mt-16 pb-8 text-center">
          <p className="text-xs text-zinc-700">
            ActionPilot AI · Built with browser-use + Gemini 2.0 Flash
          </p>
        </footer>
      </div>

      {/* ═══════════════════════════════════════════════════════
          HITL MODAL
      ═══════════════════════════════════════════════════════ */}
      <HITLModal
        isOpen={showHITL}
        jobId={activeJob?.id || ''}
        onClose={() => setShowHITL(false)}
      />
    </div>
  );
}
