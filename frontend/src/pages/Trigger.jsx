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
    const threadId = params.get("thread_id");
    if (!threadId) {
      setStatus("error");
      setMessage("No workflow ID found");
      return;
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

        {status === "error" && (
          <>
            <AlertCircle className="text-red-400 mx-auto mb-4" size={48} />
            <p className="text-red-400">{message}</p>
          </>
        )}
      </div>
    </div>
  );
}
