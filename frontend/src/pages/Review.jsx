import { useEffect, useRef, useState } from "react";
import { getWorkflowState } from "../api/rfpApi";
import { useRfpStore } from "../store/rfpStore";
import { useNavigate } from "react-router-dom";
import { Eye, Loader2, TrendingUp } from "lucide-react";

export default function Review() {
  const { threadId, state, setState } = useRfpStore();
  const navigate = useNavigate();
  const pollRef = useRef(null);

  const [selecting, setSelecting] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(null);

  useEffect(() => {
    if (!threadId) return;

    pollRef.current = setInterval(async () => {
      const res = await getWorkflowState(threadId);
      setState(res.data);
    }, 3000);

    return () => clearInterval(pollRef.current);
  }, [threadId, setState]);

  if (!state?.rfp_results) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <Loader2 className="animate-spin text-cyan-400" size={32} />
      </div>
    );
  }

  const handleSelect = async (index) => {
    setSelecting(true);
    setSelectedIndex(index);
    clearInterval(pollRef.current);

    try {
      await fetch(`http://localhost:8000/rfp/${threadId}/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision: "approve",
          rfp_index: index
        })
      });

      navigate("/pricing");
    } catch {
      alert("Selection failed");
      setSelecting(false);
    }
  };

  return (
    <div className="min-h-screen gradient-bg py-8 px-6">
      <h1 className="text-3xl font-bold mb-6">RFP Review</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {state.rfp_results.map((rfp, idx) => (
          <div key={idx} className="card p-6">
            <p className="text-slate-400 mb-2">{rfp.file_path?.split("/").pop()}</p>

            <div className="mb-4">
                {rfp.winning_probability != null ? (
                  <p className="text-xl font-bold text-emerald-400">
                    {Math.round(rfp.winning_probability * 100)}% Winning Probability
                  </p>
                ) : (
                  <p className="text-sm text-amber-400">
                    ⏳ {rfp.stage === "technical_matching"
                      ? "Technical matching in progress"
                      : "Analyzing RFP"}
                  </p>
                )}
              </div>


            <div className="h-64 bg-slate-800 rounded mb-4">
              {rfp.review_pdf_path ? (
                <iframe
                  src={`http://localhost:8000${rfp.review_pdf_path}`}
                  className="w-full h-full"
                />
              ) : (
                <Eye className="m-auto text-slate-500" />
              )}
            </div>

            <button
              disabled={selecting}
              onClick={() => handleSelect(idx)}
              className="btn-success w-full"
            >
              {selecting && selectedIndex === idx ? "Processing..." : "Approve & Continue"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
