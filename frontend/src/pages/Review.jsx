import { useEffect, useState } from "react";
import { getWorkflowState, approveRfp } from "../api/rfpApi";
import { useRfpStore } from "../store/rfpStore";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, XCircle, Eye, Loader2 } from "lucide-react";

export default function Review() {
  const { threadId, state, setState } = useRfpStore();
  const navigate = useNavigate();
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    const poll = setInterval(async () => {
      if (!threadId) return;
      const res = await getWorkflowState(threadId);
      setState(res.data);
    }, 3000);

    return () => clearInterval(poll);
  }, [threadId]);

  if (!state) return (
    <div className="min-h-screen gradient-bg flex items-center justify-center">
      <div className="card p-8">
        <Loader2 className="animate-spin text-cyan-400 mx-auto" size={32} />
        <p className="text-slate-300 mt-4">Loading review data...</p>
      </div>
    </div>
  );

  const handleApproval = async (approved) => {
    setApproving(true);
    await approveRfp(threadId, approved);

    if (approved) {
      setTimeout(() => {
        navigate("/pricing");
      }, 1500);
    } else {
      navigate("/");
    }
  };

  return (
    <div className="min-h-screen gradient-bg py-8">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Technical Review</h1>
          <p className="text-slate-400">Review the extracted technical specifications and details</p>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* PDF Viewer */}
          <div className="lg:col-span-2">
            <div className="card overflow-hidden h-96 lg:h-[600px] flex items-center justify-center bg-slate-800">
              {state.review_pdf_path ? (
                <iframe
                  src={`http://localhost:8000${state.review_pdf_path}`}
                  className="w-full h-full"
                  title="Technical Review PDF"
                />
              ) : (
                <div className="text-center">
                  <Eye size={48} className="text-slate-500 mx-auto mb-2" />
                  <p className="text-slate-400">PDF will appear here</p>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar with Details */}
          <div className="space-y-6">
            {/* Technical Review Card */}
            <div className="card p-6">
              <h3 className="text-lg font-bold mb-4 text-cyan-400">Extracted Data</h3>
              
              {state.technical_review ? (
                <div className="space-y-3 text-sm">
                  <div className="bg-slate-800 p-3 rounded-lg">
                    <p className="text-slate-400 mb-1">Technical Specs</p>
                    <p className="text-slate-200 font-mono text-xs line-clamp-4">
                      {typeof state.technical_review === 'string' 
                        ? state.technical_review.substring(0, 200)
                        : JSON.stringify(state.technical_review).substring(0, 200)}
                    </p>
                  </div>
                  {state.products_matched && (
                    <div className="bg-slate-800 p-3 rounded-lg">
                      <p className="text-slate-400 mb-1">Products Found</p>
                      <p className="text-slate-200 text-xs">{state.products_matched.length} items</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-slate-400 text-sm">Processing technical data...</p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="card p-6 bg-gradient-to-br from-slate-800 to-slate-900">
              <p className="text-slate-400 text-sm mb-4">Do you approve this technical review?</p>
              <div className="space-y-3">
                <button
                  onClick={() => handleApproval(true)}
                  disabled={approving}
                  className="btn-success w-full flex items-center justify-center gap-2"
                >
                  {approving ? <Loader2 size={20} className="animate-spin" /> : <CheckCircle2 size={20} />}
                  Approve
                </button>
                <button
                  onClick={() => handleApproval(false)}
                  disabled={approving}
                  className="btn-danger w-full flex items-center justify-center gap-2"
                >
                  <XCircle size={20} />
                  Reject
                </button>
              </div>
            </div>

            {/* Info Card */}
            <div className="card p-4 bg-blue-500/10 border-blue-500/30">
              <p className="text-sm text-blue-300">
                Once approved, the system will proceed to pricing calculation based on matched products.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
