import { useEffect, useState } from "react";
import { useRfpStore } from "../store/rfpStore";
import { useNavigate } from "react-router-dom";
import { Mail, Send, X, Home, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export default function EmailDraft() {
  const { threadId, state } = useRfpStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log('EmailDraft mounted, state:', state);
    
    // Check if we have email_draft data
    if (!state?.email_draft) {
      console.error('❌ No email draft in state');
      setError('Email draft not found. Please complete the bidding process.');
    }
  }, [state]);

  const handleSendEmail = async (approved) => {
    if (!approved) {
      // User cancelled
      navigate("/");
      return;
    }

    setSending(true);
    setError(null);

    try {
      const response = await fetch(
        `http://localhost:8000/rfp/${threadId}/approve-email?approved=true`,
        { method: 'POST' }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send email');
      }

      const result = await response.json();
      console.log('Email result:', result);

      if (result.status === 'email_sent') {
        setSent(true);
        setTimeout(() => navigate("/"), 3000);
      } else {
        setError(result.message || 'Failed to send email');
      }
    } catch (err) {
      console.error('Error sending email:', err);
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  if (error && !state?.email_draft) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center px-4">
        <div className="card p-8 max-w-md w-full">
          <div className="flex items-start gap-4">
            <AlertCircle size={24} className="text-red-400 shrink-0 mt-1" />
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

  if (sent) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center px-4">
        <div className="card p-8 max-w-md w-full text-center">
          <CheckCircle2 size={64} className="text-green-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Email Sent!</h2>
          <p className="text-slate-400 mb-4">
            Your bid submission email has been sent successfully.
          </p>
          <p className="text-sm text-slate-500">
            Redirecting to home...
          </p>
        </div>
      </div>
    );
  }

  const emailDraft = state?.email_draft || {};

  return (
    <div className="min-h-screen gradient-bg py-8">
      <div className="max-w-4xl mx-auto px-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-linear-to-r from-blue-500 to-cyan-500 rounded-lg">
              <Mail size={24} className="text-white" />
            </div>
            <h1 className="text-4xl font-bold">Email Draft</h1>
          </div>
          <p className="text-slate-400">Review and send your bid submission email</p>
        </div>

        {/* Email Preview */}
        <div className="card mb-8">
          <div className="border-b border-slate-700 p-6">
            <div className="grid gap-4">
              <div>
                <label className="text-sm text-slate-500 block mb-1">To:</label>
                <div className="text-slate-200">{emailDraft.to}</div>
              </div>
              <div>
                <label className="text-sm text-slate-500 block mb-1">From:</label>
                <div className="text-slate-200">{emailDraft.from}</div>
              </div>
              <div>
                <label className="text-sm text-slate-500 block mb-1">Subject:</label>
                <div className="text-slate-200 font-semibold">{emailDraft.subject}</div>
              </div>
            </div>
          </div>

          <div className="p-6 bg-slate-800">
            <label className="text-sm text-slate-500 block mb-3">Message:</label>
            <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-slate-200">
              {emailDraft.body}
            </pre>
          </div>
        </div>

        {error && (
          <div className="card p-4 mb-6 bg-red-500/10 border-red-500/30">
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <button
            onClick={() => handleSendEmail(true)}
            disabled={sending}
            className="btn-primary flex items-center justify-center gap-2 group"
          >
            {sending ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                Sending Email...
              </>
            ) : (
              <>
                <Send size={20} className="group-hover:scale-110 transition-transform" />
                Send Email
              </>
            )}
          </button>

          <button
            onClick={() => handleSendEmail(false)}
            disabled={sending}
            className="btn-secondary flex items-center justify-center gap-2 group"
          >
            <X size={20} className="group-hover:scale-110 transition-transform" />
            Cancel
          </button>
        </div>

        {/* Info Box */}
        <div className="card p-6 bg-linear-to-r from-blue-500/10 to-cyan-500/10 border-blue-500/30">
          <p className="text-slate-300 mb-4">📧 Email Details</p>
          <ul className="space-y-2 text-sm text-slate-400">
            <li className="flex items-center gap-2">
              <span className="text-cyan-400">→</span> Email will be sent via Gmail API
            </li>
            <li className="flex items-center gap-2">
              <span className="text-cyan-400">→</span> Final bid document will be attached
            </li>
            <li className="flex items-center gap-2">
              <span className="text-cyan-400">→</span> You can cancel anytime before sending
            </li>
          </ul>
        </div>

        {/* Back Button */}
        <button
          onClick={() => navigate("/")}
          className="btn-secondary w-full mt-6 flex items-center justify-center gap-2"
          disabled={sending}
        >
          <Home size={20} />
          Back to Home
        </button>
      </div>
    </div>
  );
}
