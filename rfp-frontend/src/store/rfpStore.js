import { create } from "zustand";

export const useRfpStore = create((set) => ({
  threadId: null,
  state: null,
  status: "idle",

  setThreadId: (threadId) => set({ threadId }),
  setState: (state) => set({ state }),
  setStatus: (status) => set({ status }),
}));
