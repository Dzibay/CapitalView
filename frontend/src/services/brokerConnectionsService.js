import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

const EP = API_ENDPOINTS.BROKER_CONNECTIONS;

/** Подключения брокеров. Токен уходит на сервер и обратно не возвращается — только маска. */
export default {
  async list() {
    const res = await apiClient.get(EP.LIST);
    return res.data.connections || [];
  },

  /** Проверка токена у брокера без импорта: { accounts, already_connected } */
  async checkToken(broker_id, token) {
    const res = await apiClient.post(EP.CHECK_TOKEN, { broker_id, token });
    return res.data;
  },

  /** «Обновить портфели»: { results, tasks, message } */
  async syncAll() {
    const res = await apiClient.post(EP.SYNC_ALL, {});
    return res.data;
  },

  async sync(connectionId) {
    const res = await apiClient.post(EP.SYNC(connectionId), {});
    return res.data;
  },

  async replaceToken(connectionId, token, syncNow = true) {
    const res = await apiClient.put(EP.TOKEN(connectionId), { token, sync_now: syncNow });
    return res.data;
  },

  async setAutoSync(connectionId, autoSync) {
    const res = await apiClient.patch(EP.ITEM(connectionId), { auto_sync: autoSync });
    return res.data;
  },

  async remove(connectionId) {
    const res = await apiClient.delete(EP.ITEM(connectionId));
    return res.data;
  },
};
