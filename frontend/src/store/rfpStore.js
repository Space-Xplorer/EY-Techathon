import { create } from "zustand";

export const useRfpStore = create((set) => ({
  threadId: null,
  state: null,
  status: "idle",
  
  // Track all processed files for comparison
  allFiles: [], // Array of {file_index, file_path, technical_review, review_pdf_path, total_cost}
  selectedFileIndex: null, // Which file user chose for final bid

  setThreadId: (threadId) => set({ threadId }),
  setState: (state) => set({ state }),
  setStatus: (status) => set({ status }),
  
  // Add file to the processed files list
  addProcessedFile: (fileData) => set((store) => ({
    allFiles: [...store.allFiles, fileData]
  })),
  
  // Set which file was selected for final pricing
  setSelectedFileIndex: (index) => set({ selectedFileIndex: index }),
  
  // Clear all data
  reset: () => set({ threadId: null, state: null, status: "idle", allFiles: [], selectedFileIndex: null })
}));
