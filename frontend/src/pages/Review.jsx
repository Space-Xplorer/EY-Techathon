import { useEffect, useRef, useState } from "react";
import { getWorkflowState } from "../api/rfpApi";
import { useRfpStore } from "../store/rfpStore";
import { useNavigate } from "react-router-dom";
import { Eye, Loader2, TrendingUp } from "lucide-react";

export default function Review() {
  const { threadId, state, setState } = useRfpStore();
  const navigate = useNavigate();
  const [approving, setApproving] = useState(false);
  const [isLoadingNextFile, setIsLoadingNextFile] = useState(false);

  useEffect(() => {
    const poll = setInterval(async () => {
      if (!threadId) return;
      try {
        const res = await getWorkflowState(threadId);
        setState(res.data);
      } catch (error) {
        console.error("Polling error:", error);
      }
    }, 2000);

    return () => clearInterval(pollRef.current);
  }, [threadId, setState]);

  // Hide loading overlay when review PDF loads
  useEffect(() => {
    if (isLoadingNextFile && state?.review_pdf_path) {
      setIsLoadingNextFile(false);
    }
  }, [state?.review_pdf_path, isLoadingNextFile]);

  if (!state) return (
    <div className="min-h-screen gradient-bg flex items-center justify-center">
      <div className="card p-8">
        <Loader2 className="animate-spin text-cyan-400 mx-auto" size={32} />
        <p className="text-slate-300 mt-4">Loading review data...</p>
      </div>
    );
  }

  const handleApproval = async (approved) => {
    setApproving(true);
    try {
      const response = await approveRfp(threadId, approved);
      
      if (approved) {
        // Check if there are more files to approve
        if (response?.data?.status === "next_file") {
          // More files exist - show loading and let polling fetch the next file
          setIsLoadingNextFile(true);
          setApproving(false);
          // The polling effect will automatically update state with new file data
        } else if (response?.data?.status === "all_complete") {
          // All files approved - go to file selection page to choose which to use
          setTimeout(() => {
            navigate("/file-selection");
          }, 1500);
        } else {
          // Default behavior - go to file selection
          setTimeout(() => {
            navigate("/file-selection");
          }, 1500);
        }
      } else {
        navigate("/");
      }
    } catch (error) {
      console.error("Approval error:", error);
      setApproving(false);
    }
  };

  return (
    <div className="min-h-screen gradient-bg py-8">
      <div className="max-w-7xl mx-auto px-6">
        {/* Loading next file overlay */}
        {isLoadingNextFile && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="card p-8 text-center">
              <Loader2 className="animate-spin text-cyan-400 mx-auto mb-4" size={40} />
              <h3 className="text-xl font-semibold">Loading next file...</h3>
              <p className="text-slate-400 mt-2">Processing the next RFP in your batch</p>
            </div>
          </div>
        )}

        {/* Header with Batch Progress */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Technical Review</h1>
          <p className="text-slate-400">Review the extracted technical specifications and details</p>
          {state?.batch_progress && (
            <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <p className="text-sm text-blue-300">
                Processing batch: File {state.batch_progress.current_file_index + 1} of {state.batch_progress.total_files}
              </p>
              <div className="w-full h-1 bg-slate-700 rounded-full mt-2 overflow-hidden">
                <div 
                  className="h-full bg-linear-to-r from-blue-500 to-cyan-500 transition-all"
                  style={{ width: `${((state.batch_progress.current_file_index + 1) / state.batch_progress.total_files) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* PDF Viewer */}
          <div className="lg:col-span-2">
            <div className="card overflow-hidden h-96 lg:h-150 flex items-center justify-center bg-slate-800">
              {state.review_pdf_path ? (
                <iframe
                  src={`http://localhost:8000${rfp.review_pdf_path}`}
                  className="w-full h-full"
                />
              ) : (
                <Eye className="m-auto text-slate-500" />
              )}
            </div>

            {/* Action Buttons */}
            <div className="card p-6 bg-linear-to-br from-slate-800 to-slate-900">
              <p className="text-slate-400 text-sm mb-4">Do you approve this technical review?</p>
              <div className="space-y-3">
                <button
                  onClick={() => handleApproval(true)}
                  disabled={approving || isLoadingNextFile}
                  className="btn-success w-full flex items-center justify-center gap-2"
                >
                  {approving ? <Loader2 size={20} className="animate-spin" /> : <CheckCircle2 size={20} />}
                  {approving ? 'Processing...' : `Approve${state?.batch_progress?.current_file_index + 1 < state?.batch_progress?.total_files ? ' & Continue' : ''}`}
                </button>
                <button
                  onClick={() => handleApproval(false)}
                  disabled={approving || isLoadingNextFile}
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
                {state?.batch_progress?.current_file_index + 1 === state?.batch_progress?.total_files
                  ? 'This is the last file. After approval, you\'ll proceed to pricing.'
                  : `After approval, you'll review the next file (${state?.batch_progress?.current_file_index + 2} of ${state?.batch_progress?.total_files}).`}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
