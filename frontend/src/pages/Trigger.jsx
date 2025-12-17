import { useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useRfpStore } from "../store/rfpStore";
import { Loader2, CheckCircle2, AlertCircle, Zap } from "lucide-react";

export default function Trigger() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { setThreadId } = useRfpStore();

  const [status, setStatus] = useState("processing");
  const [message, setMessage] = useState("Starting workflow...");

  useEffect(() => {
    const threadId = params.get('thread_id');
    
    if (threadId) {
      setThreadId(threadId);
      setStatus('processing');
      setMessage('Processing all RFPs automatically. This may take a few minutes...');
      
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`http://localhost:8000/rfp/${threadId}/state`);
          const state = await response.json();
          
          // Check if processing is complete
          const batchProgress = state.batch_progress || {};
          if (batchProgress.processing_complete) {
            clearInterval(pollInterval);
            setStatus('ready');
            setMessage('All RFPs processed! Redirecting to selection...');
            
            setTimeout(() => {
              navigate('/file-selection');
            }, 1500);
          }
        } catch (error) {
          console.error('Polling error:', error);
        }
      }, 2000);

      return () => clearInterval(pollInterval);
    } else {
      setStatus('error');
      setMessage('No workflow ID found. Please upload files from home page.');
    }
  }, [params, setThreadId, navigate]);

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center">
      <div className="card p-10 text-center max-w-md">
        {status === "processing" && (
          <>
            <Loader2 className="animate-spin text-cyan-400 mx-auto mb-4" size={48} />
            <h2 className="text-xl font-semibold">Processing RFPs</h2>
            <p className="text-slate-400 mt-2">{message}</p>
          </>
        )}

        {status === "ready" && (
          <>
            <CheckCircle2 className="text-emerald-400 mx-auto mb-4" size={48} />
            <h2 className="text-xl font-semibold">Ready for Review</h2>
            <p className="text-slate-400 mt-2">{message}</p>
          </>
        )}

        {status === 'processing' && (
          <div className="mt-6 bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-sm text-blue-300">
            <div className="flex gap-2">
              <Zap size={20} className="shrink-0" />
              <p>This may take a few minutes depending on document complexity. Please don't close this window.</p>
            </div>
          </div>
        )}

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
