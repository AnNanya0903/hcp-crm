import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import * as api from '../api/client';

export const loadHcps = createAsyncThunk('interactions/loadHcps', async () => api.fetchHcps());

export const loadInteractions = createAsyncThunk(
  'interactions/loadInteractions',
  async (hcpId) => api.fetchInteractions(hcpId)
);

export const submitInteraction = createAsyncThunk(
  'interactions/submitInteraction',
  async (payload) => api.createInteraction(payload)
);

export const editInteraction = createAsyncThunk(
  'interactions/editInteraction',
  async ({ id, patch }) => api.updateInteraction(id, patch)
);

const initialState = {
  hcps: [],
  interactions: [],
  status: 'idle',
  lastSubmission: null,
  error: null,
};

const interactionsSlice = createSlice({
  name: 'interactions',
  initialState,
  reducers: {
    clearLastSubmission(state) {
      state.lastSubmission = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadHcps.fulfilled, (state, action) => {
        state.hcps = action.payload;
      })
      .addCase(loadInteractions.fulfilled, (state, action) => {
        state.interactions = action.payload;
      })
      .addCase(submitInteraction.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(submitInteraction.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.lastSubmission = action.payload;
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.error.message;
      })
      .addCase(editInteraction.fulfilled, (state, action) => {
        state.lastSubmission = action.payload;
      });
  },
});

export const { clearLastSubmission } = interactionsSlice.actions;
export default interactionsSlice.reducer;
