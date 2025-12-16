import { useEffect, useState } from "react";
import { useRfpStore } from "../store/rfpStore";
import { getWorkflowState } from "../api/rfpApi";
import { useNavigate } from "react-router-dom";
import { Loader2, Home, FileText, Download } from "lucide-react";

export default function FinalBid() {
  const { threadId, state, setState } = useRfpStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [bidText, setBidText] = useState("");
  const [bidPath, setBidPath] = useState(null);

  useEffect(() => {
    let poll;

    const load = async () => {
      if (!threadId) return;

      poll = setInterval(async () => {
        const res = await getWorkflowState(threadId);
        setState(res.data);

        if (res.data?.final_bid?.text) {
          setBidText(res.data.final_bid.text);
          setBidPath(res.data.final_bid.path);
          setLoading(false);
          clearInterval(poll);
        }
      }, 2000);
    };

    load();

    return () => poll && clearInterval(poll);
  }, [threadId, setState]);

  if (loading) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="card p-8 text-center">
          <Loader2 className="animate-spin text-cyan-400 mx-auto mb-4" size={32} />
          <p className="text-slate-400">Generating final bid…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg py-8 px-6 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <FileText /> Final Bid
      </h1>

      <div className="card p-6 mb-6 bg-slate-900">
        <pre className="whitespace-pre-wrap text-sm leading-relaxed">
          {bidText}
        </pre>
      </div>

      {bidPath && (
        <a
          href={`http://localhost:8000${bidPath}`}
          download
          className="btn-primary w-full mb-4 flex items-center justify-center gap-2"
        >
          <Download /> Download Final Bid
        </a>
      )}

      <button onClick={() => navigate("/")} className="btn-secondary w-full">
        <Home /> Back to Home
      </button>
    </div>
  );
}
