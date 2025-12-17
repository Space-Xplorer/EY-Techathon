import { useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useRfpStore } from "../store/rfpStore";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export default function Trigger() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { setThreadId } = useRfpStore();

  const [status, setStatus] = useState("processing");
  const [message, setMessage] = useState("Starting workflow...");

  useEffect(() => {
    const threadId = searchParams.get('thread_id');
    
    if (threadId) {
      setThreadId(threadId);
      setStatus('processing');
      setStatusMessage('Processing all RFPs automatically. This may take a few minutes...');
      
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`http://localhost:8000/rfp/${threadId}/state`);
          const state = await response.json();
          
          // Check if processing is complete
          const batchProgress = state.batch_progress || {};
          if (batchProgress.processing_complete) {
            clearInterval(pollInterval);
            setStatus('ready');
            setStatusMessage('All RFPs processed! Redirecting to selection...');
            setProgress({ current: 3, total: 5 });
            
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
      setStatusMessage('No workflow ID found. Please upload files from home page.');
    }

    setThreadId(threadId);

    const poll = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/rfp/${threadId}/state`);
        const state = await res.json();

        // ✅ MOVE TO REVIEW WHEN RFP RESULTS EXIST
        if (Array.isArray(state.rfp_results) && state.rfp_results.length > 0) {
          clearInterval(poll);
          setStatus("ready");
          setMessage("Analysis complete. Redirecting to review...");
          setTimeout(() => navigate("/review"), 1200);
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);

    return () => clearInterval(poll);
  }, []);

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
          </>
        )}

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
                  className="h-full bg-linear-to-r from-blue-500 to-cyan-500 transition-all duration-500"
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
                <Zap size={20} className="shrink-0" />
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
