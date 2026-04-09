/**
 * Коэффициенты прозрачности прогнозных столбцов PayoutsChartWidget (множитель к α заливки).
 * 1 — без ослабления (факт); меньше 1 — слабее/прозрачнее.
 */
export const PAYOUTS_FORECAST_OPACITY = {
  /** mode=future — все столбцы считаются прогнозом */
  futureMode: 0.45,
  /** mode=all — период целиком в будущем */
  allFutureBucket: 0.38,
  /** mode=all — период пересекает «сегодня» (текущий месяц/квартал/год) */
  allStraddleBucket: 0.58
}
