import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

export const triggerWorkflow = (payload) =>
  api.post("/rfp/trigger", payload);

export const getWorkflowState = (threadId) =>
  api.get(`/rfp/${threadId}/state`);

export const approveRfp = (threadId, approved) =>
  api.post(`/rfp/${threadId}/approve`, { approved });
