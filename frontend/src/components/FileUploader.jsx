import { useState, useRef } from 'react';
import { Upload, X, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

const FileUploader = ({ onFilesUploaded }) => {
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    addFiles(selectedFiles);
  };

  const addFiles = (newFiles) => {
    const pdfFiles = newFiles.filter(file => file.type === 'application/pdf');
    
    if (pdfFiles.length !== newFiles.length) {
      setUploadError('Only PDF files are allowed');
      setTimeout(() => setUploadError(null), 3000);
    }

    if (files.length + pdfFiles.length > 10) {
      setUploadError('Maximum 10 files allowed');
      setTimeout(() => setUploadError(null), 3000);
      return;
    }

    setFiles(prev => [...prev, ...pdfFiles]);
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setUploadError('Please select at least one file');
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });

      const response = await fetch('http://localhost:8000/rfp/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const data = await response.json();
      
      if (onFilesUploaded) {
        onFilesUploaded(data);
      }

      setFiles([]);
    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error.message);
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="w-full">
      {/* Upload Error Alert */}
      {uploadError && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3 text-red-400 animate-in fade-in slide-in-from-top-2">
          <AlertCircle size={20} className="shrink-0" />
          <span className="text-sm">{uploadError}</span>
        </div>
      )}

      {/* Drop Zone */}
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300
          ${isDragging 
            ? 'border-cyan-500 bg-cyan-500/10 scale-105' 
            : 'border-slate-700 hover:border-cyan-500/50 hover:bg-slate-800/50'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf"
          onChange={handleFileSelect}
          className="hidden"
        />

        <Upload 
          size={48} 
          className={`mx-auto mb-4 transition-colors ${isDragging ? 'text-cyan-400' : 'text-slate-400'}`}
        />

        <h3 className="text-xl font-semibold mb-2">
          {isDragging ? 'Drop files here' : 'Upload RFP Documents'}
        </h3>
        
        <p className="text-slate-400 mb-4">
          Drag & drop PDF files here, or click to browse
        </p>
        
        <p className="text-sm text-slate-500">
          Maximum 10 files • PDF only • Up to 50MB per file
        </p>
      </div>

      {/* Files List */}
      {files.length > 0 && (
        <div className="mt-8 space-y-4">
          <h4 className="font-semibold text-slate-200 flex items-center gap-2">
            <FileText size={20} className="text-blue-400" />
            Selected Files ({files.length})
          </h4>

          {files.map((file, index) => (
            <div
              key={index}
              className="card p-4 flex items-center justify-between group hover:border-cyan-500/30"
            >
              <div className="flex items-center gap-3 flex-1">
                <FileText size={24} className="text-blue-400" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-100 truncate">
                    {file.name}
                  </p>
                  <p className="text-sm text-slate-400">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>

              <button
                onClick={() => removeFile(index)}
                className="p-2 hover:bg-red-500/10 rounded-lg transition-colors ml-4"
                title="Remove file"
              >
                <X size={20} className="text-red-400" />
              </button>
            </div>
          ))}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={uploading || files.length === 0}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {uploading ? (
              <>
                <Loader2 size={20} className="animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <CheckCircle2 size={20} />
                Upload {files.length} File{files.length > 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default FileUploader;
