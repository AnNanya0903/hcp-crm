import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import * as api from '../api/client';

const SESSION_ID = `session-${Date.now()}`;

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (message) => {
    const response = await api.sendChatMessage(SESSION_ID, message);
    return { message, response };
  }
);

const initialState = {
  sessionId: SESSION_ID,
  messages: [], // { role: 'user' | 'agent', text }
  preview: null,
  toolUsed: null,
  status: 'idle',
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.status = 'loading';
        state.messages.push({ role: 'user', text: action.meta.arg });
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = 'succeeded';
        const { response } = action.payload;
        state.messages.push({ role: 'agent', text: response.reply });
        state.preview = response.preview || null;
        state.toolUsed = response.tool_used || null;
      })
      .addCase(sendMessage.rejected, (state) => {
        state.status = 'failed';
        state.messages.push({ role: 'agent', text: 'Something went wrong — please try again.' });
      });
  },
});

export default chatSlice.reducer;
