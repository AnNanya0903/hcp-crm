import axios from 'axios';

const client = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
});

export const fetchHcps = () => client.get('/interactions/hcps').then((r) => r.data);

export const createHcp = (payload) => client.post('/hcps', payload).then((r) => r.data);

export const fetchInteractions = (hcpId) =>
  client.get('/interactions', { params: hcpId ? { hcp_id: hcpId } : {} }).then((r) => r.data);

export const createInteraction = (payload) =>
  client.post('/interactions', payload).then((r) => r.data);

export const updateInteraction = (id, patch) =>
  client.patch(`/interactions/${id}`, patch).then((r) => r.data);

export const sendChatMessage = (sessionId, message) =>
  client.post('/chat', { session_id: sessionId, message }).then((r) => r.data);

export default client;
