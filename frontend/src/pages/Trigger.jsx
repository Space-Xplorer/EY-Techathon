import { useNavigate, useSearchParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { useRfpStore } from "../store/rfpStore";
import { CheckCircle2, Loader2, AlertCircle, Zap } from "lucide-react";

export default function Trigger() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setThreadId } = useRfpStore();
  const [status, setStatus] = useState('initializing');
  const [statusMessage, setStatusMessage] = useState('');
  const [progress, setProgress] = useState({ current: 1, total: 5 });

  useEffect(() => {
    const threadId = searchParams.get('thread_id');
    
    if (threadId) {
      setThreadId(threadId);
      setStatus('processing');
      setStatusMessage('Workflow started. Sales agent analyzing RFP...');
      
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`http://localhost:8000/rfp/${threadId}/state`);
          const state = await response.json();
          
          if (state.review_pdf_path && !state.human_approved) {
            clearInterval(pollInterval);
            setStatus('ready');
            setStatusMessage('Analysis complete! Ready for review.');
            setProgress({ current: 3, total: 5 });
            
            setTimeout(() => {
              navigate('/review');
            }, 1500);
          }
        } catch (error) {
          console.error('Polling error:', error);
        }
      }, 2000);

      return () => clearInterval(pollInterval);
    } else {
      setStatus('error');
      setStatusMessage('No workflow ID found. Please upload files from home page.');
    }
  }, [searchParams, setThreadId, navigate]);

  const steps = [
    { label: 'Upload', icon: '📤', active: true },
    { label: 'Sales Analysis', icon: '📊', active: status !== 'initializing' },
    { label: 'Technical Review', icon: '🔧', active: false },
    { label: 'Pricing', icon: '💰', active: false },
    { label: 'Final Bid', icon: '✅', active: false }
  ];

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center px-4">
      <div className="max-w-2xl w-full">
        <div className="card p-8 border-slate-700">
          <div className="flex justify-center mb-8">
            {status === 'processing' && (
              <div className="relative">
                <Loader2 size={64} className="text-cyan-400 animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-12 h-12 bg-cyan-500/20 rounded-full animate-pulse" />
                </div>
              </div>
            )}
            
            {status === 'ready' && (
              <CheckCircle2 size={64} className="text-emerald-400" />
            )}
            
            {status === 'error' && (
              <AlertCircle size={64} className="text-red-400" />
            )}
          </div>

          <h2 className="text-3xl font-bold text-center mb-4">
            {status === 'processing' && 'Processing RFP'}
            {status === 'ready' && 'Analysis Complete'}
            {status === 'error' && 'Error'}
          </h2>

          <p className="text-center text-slate-300 mb-8 text-lg">
            {statusMessage}
          </p>

          {status === 'processing' && (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-slate-300">Progress</span>
                <span className="text-sm text-slate-400">{progress.current} of {progress.total}</span>
              </div>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                />
              </div>
            </div>
          )}

          <div className="mb-8">
            <div className="grid grid-cols-5 gap-2">
              {steps.map((step, idx) => (
                <div key={idx} className="flex flex-col items-center">
                  <div className={`text-3xl mb-2 transition-all ${step.active ? 'scale-110' : 'scale-100'}`}>
                    {step.icon}
                  </div>
                  <p className={`text-xs text-center transition-colors ${step.active ? 'text-slate-200' : 'text-slate-500'}`}>
                    {step.label}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {status === 'processing' && (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-sm text-blue-300">
              <div className="flex gap-2">
                <Zap size={20} className="flex-shrink-0" />
                <p>This may take a few minutes depending on document complexity. Please don't close this window.</p>
              </div>
            </div>
          )}
        </div>

        {status === 'error' && (
          <div className="mt-6 flex justify-center">
            <button 
              onClick={() => navigate('/')}
              className="btn-secondary"
            >
              Back to Home
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
