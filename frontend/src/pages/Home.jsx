import { useNavigate } from "react-router-dom";
import { useState } from "react";
import FileUploader from "../components/FileUploader";
import { Sparkles, Zap, Brain, FileText, ArrowRight, CheckCircle2 } from "lucide-react";

export default function Home() {
  const navigate = useNavigate();
  const [uploadResult, setUploadResult] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleFilesUploaded = async (data) => {
    console.log('Files uploaded:', data);
    setUploadResult(data);
    setIsProcessing(true);

    try {
      const response = await fetch('http://localhost:8000/rfp/process-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: data.thread_id,
          file_paths: data.file_paths
        })
      });

      if (response.ok) {
        setTimeout(() => {
          navigate(`/trigger?thread_id=${data.thread_id}`);
        }, 1000);
      }
    } catch (error) {
      console.error('Failed to process RFPs:', error);
      setIsProcessing(false);
    }
  };

  const features = [
    {
      icon: FileText,
      title: "Multi-File Upload",
      description: "Upload up to 10 RFP documents at once with drag & drop support",
      color: "from-blue-500 to-cyan-500"
    },
    {
      icon: Brain,
      title: "AI-Powered Analysis",
      description: "Automated processing with Sales, Technical, and Pricing agents",
      color: "from-purple-500 to-pink-500"
    },
    {
      icon: Zap,
      title: "Fast Processing",
      description: "Generate complete bids in minutes with LLM-powered extraction",
      color: "from-amber-500 to-orange-500"
    }
  ];

  const steps = [
    { number: "01", label: "Upload RFPs", icon: "📤" },
    { number: "02", label: "Sales Analysis", icon: "📊" },
    { number: "03", label: "Technical Review", icon: "🔧" },
    { number: "04", label: "Pricing", icon: "💰" },
    { number: "05", label: "Final Bid", icon: "✅" }
  ];

  return (
    <div className="min-h-screen gradient-bg">
      {/* Navigation Bar */}
      <nav className="border-b border-slate-800 glass sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-linear-to-r from-blue-500 to-cyan-500 rounded-lg">
              <Sparkles size={24} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold gradient-text">RFP Orchestrator</h1>
          </div>
          <span className="text-sm text-slate-400">v1.0 - Beta</span>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden py-20">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl" />
        </div>
        
        <div className="relative max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <div className="inline-block mb-6">
              <span className="text-sm font-semibold text-cyan-400 bg-cyan-500/10 px-4 py-2 rounded-full border border-cyan-500/30">
                Powered by AI Agents
              </span>
            </div>
            <h2 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
              Intelligent RFP
              <span className="block gradient-text">Orchestration Platform</span>
            </h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-8">
              Transform your RFP process with AI-driven analysis, automated pricing, and intelligent bid generation
            </p>
          </div>

          {/* File Uploader */}
          <div className="max-w-4xl mx-auto mb-16">
            <FileUploader onFilesUploaded={handleFilesUploaded} />
          </div>

          {/* Upload Result Toast */}
          {uploadResult && (
            <div className="max-w-2xl mx-auto mb-16 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="card p-6 bg-linear-to-r from-emerald-500/10 to-teal-500/10 border-emerald-500/30">
                <div className="flex items-center gap-4">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 shrink-0" />
                  <div>
                    <h3 className="font-semibold text-emerald-400">Upload Successful!</h3>
                    <p className="text-sm text-slate-400">{uploadResult.files_uploaded} file(s) queued for processing. Initializing workflow...</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Process Flow */}
      <section className="py-16 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6">
          <h3 className="text-2xl font-bold mb-12 text-center">Our Process</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 md:gap-2">
            {steps.map((step, idx) => (
              <div key={idx} className="flex flex-col items-center">
                <div className="mb-3 text-4xl">{step.icon}</div>
                <div className="text-xs font-semibold text-cyan-400 mb-1">{step.number}</div>
                <p className="text-sm text-slate-400 text-center">{step.label}</p>
                {idx < steps.length - 1 && (
                  <ArrowRight className="text-slate-700 mt-4 -rotate-90 md:rotate-0 hidden md:block" size={20} />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6">
          <h3 className="text-3xl font-bold mb-12 text-center">Powerful Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {features.map((feature, idx) => {
              const Icon = feature.icon;
              return (
                <div key={idx} className="card-interactive group p-8 hover:border-cyan-500/50">
                  <div className={`inline-flex p-3 rounded-lg bg-linear-to-r ${feature.color} text-white mb-4 group-hover:scale-110 transition-transform`}>
                    <Icon size={24} />
                  </div>
                  <h4 className="text-xl font-semibold mb-3">{feature.title}</h4>
                  <p className="text-slate-400">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 border-t border-slate-800">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h3 className="text-3xl font-bold mb-4">Ready to Transform Your RFP Process?</h3>
          <p className="text-slate-400 mb-8">Upload your RFP documents above to get started. Our AI agents will handle the rest.</p>
          <div className="flex gap-4 justify-center">
            <button className="btn-primary flex items-center gap-2">
              Get Started <ArrowRight size={20} />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 mt-20">
        <div className="max-w-7xl mx-auto px-6 text-center text-slate-400 text-sm">
          <p>© 2024 RFP Orchestrator. Powered by LangGraph & Groq API.</p>
        </div>
      </footer>
    </div>
  );
}
