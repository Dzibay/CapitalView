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
  },

  async addPricesBatch(asset_id, prices) {
    // prices - массив объектов { price, date }
    const payload = { asset_id, prices };
    const res = await apiClient.post(API_ENDPOINTS.ASSETS.ADD_PRICES_BATCH, payload);
    return res.data;
  },

  async moveAsset(portfolio_asset_id, target_portfolio_id) {
    const payload = { target_portfolio_id };
    const res = await apiClient.post(API_ENDPOINTS.ASSETS.MOVE(portfolio_asset_id), payload);
    return res.data;
  },

  async getAssetInfo(asset_id) {
    const res = await apiClient.get(API_ENDPOINTS.ASSETS.GET_INFO(asset_id));
    return res.data;
  },

  async getAssetPriceHistory(asset_id, start_date = null, end_date = null, limit = 1000) {
    const params = { limit };
    if (start_date) params.start_date = start_date;
    if (end_date) params.end_date = end_date;
    const res = await apiClient.get(API_ENDPOINTS.ASSETS.GET_PRICES(asset_id), { params });
    return res.data;
  },

  async getPortfolioAssetInfo(portfolio_asset_id) {
    const res = await apiClient.get(API_ENDPOINTS.ASSETS.GET_PORTFOLIO_ASSET_INFO(portfolio_asset_id));
    return res.data;
  }
};
