import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export default {
  async addAsset(assetData) {
    const res = await apiClient.post(API_ENDPOINTS.ASSETS.ADD, assetData);
    return res.data;
  },

  async deleteAsset(assetId) {
    const res = await apiClient.delete(API_ENDPOINTS.ASSETS.DELETE(assetId));
    return res.data;
  },

  async addPrice(asset_id, price, date) {
    const payload = { asset_id, price, date };
    const res = await apiClient.post(API_ENDPOINTS.ASSETS.ADD_PRICE, payload);
    return res.data;
  }
};
