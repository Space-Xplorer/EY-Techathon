import { useEffect, useState } from "react";
import { useRfpStore } from "../store/rfpStore";
import { getWorkflowState } from "../api/rfpApi";
import { useNavigate } from "react-router-dom";
import { Loader2, Download, Printer, Home, AlertCircle, FileText } from "lucide-react";

export default function FinalBid() {
  const { threadId, state, setState } = useRfpStore();
  const navigate = useNavigate();
  const [bidText, setBidText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchBid = async () => {
      if (!threadId) {
        setError("No thread ID found");
        setLoading(false);
        return;
      }
      
      try {
        const res = await getWorkflowState(threadId);
        setState(res.data);

        const response = await fetch("http://localhost:8000/files/output/final_bid.txt");
        if (response.ok) {
          const text = await response.text();
          setBidText(text);
          setError(null);
        } else {
          setError("Bid file not found. Please wait for processing to complete.");
        }
      } catch (err) {
        console.error("Error fetching bid:", err);
        setError("Failed to load bid document: " + err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchBid();
  }, [threadId]);

  if (loading) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="card p-12 text-center">
          <Loader2 className="animate-spin text-cyan-400 mx-auto mb-4" size={32} />
          <h2 className="text-xl font-semibold">Loading final bid...</h2>
          <p className="text-slate-400 mt-2">Compiling all RFP responses</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center px-4">
        <div className="card p-8 max-w-md w-full">
          <div className="flex items-start gap-4">
            <AlertCircle size={24} className="text-red-400 flex-shrink-0 mt-1" />
            <div>
              <h2 className="text-xl font-semibold text-red-400 mb-2">Error</h2>
              <p className="text-slate-400 mb-6">{error}</p>
              <button
                onClick={() => navigate("/")}
                className="btn-secondary w-full"
              >
                Back to Home
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg py-8">
      <div className="max-w-5xl mx-auto px-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
              <FileText size={24} className="text-white" />
            </div>
            <h1 className="text-4xl font-bold">Final Bid Document</h1>
          </div>
          <p className="text-slate-400">Complete RFP response ready for submission</p>
        </div>

        {/* Document Viewer */}
        <div className="card mb-8 overflow-hidden">
          <div className="bg-slate-800 p-8 max-h-[600px] overflow-auto">
            <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-slate-200">
              {bidText}
            </pre>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <a 
            href="http://localhost:8000/files/output/final_bid.txt" 
            download="final_bid.txt"
            className="btn-primary flex items-center justify-center gap-2 group"
          >
            <Download size={20} className="group-hover:scale-110 transition-transform" />
            Download as TXT
          </a>
          
          <button
            onClick={() => window.print()}
            className="btn-success flex items-center justify-center gap-2 group"
          >
            <Printer size={20} className="group-hover:scale-110 transition-transform" />
            Print Document
          </button>
        </div>

        {/* Navigation */}
        <div className="card p-6 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border-blue-500/30 mb-8">
          <p className="text-slate-300 mb-4">What's next?</p>
          <ul className="space-y-2 text-sm text-slate-400 mb-4">
            <li className="flex items-center gap-2">
              <span className="text-cyan-400">→</span> Review the bid document for accuracy
            </li>
            <li className="flex items-center gap-2">
              <span className="text-cyan-400">→</span> Download and submit to the RFP portal
            </li>
            <li className="flex items-center gap-2">
              <span className="text-cyan-400">→</span> Process another RFP or modify this one
            </li>
          </ul>
        </div>

        {/* Back Button */}
        <button
          onClick={() => navigate("/")}
          className="btn-secondary w-full flex items-center justify-center gap-2"
        >
          <Home size={20} />
          Back to Home
        </button>
      </div>
    </div>
  );
}
