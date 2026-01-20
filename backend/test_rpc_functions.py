"""
Скрипт для тестирования RPC функций с аналитикой производительности.

Использование:
    python test_rpc_functions.py                    # Тестирует все функции
    python test_rpc_functions.py --function refresh_asset_latest_prices  # Тестирует конкретную функцию
    python test_rpc_functions.py --iterations 5     # Запускает каждую функцию 5 раз
    python test_rpc_functions.py --batch-size 1000  # Тестирует с разными размерами батчей
"""

import asyncio
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse
import sys
import os

# Добавляем путь к app для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.supabase_service import rpc, table_select, get_supabase_client


class RPCTester:
    """Класс для тестирования RPC функций с аналитикой."""
    
    def __init__(self):
        self.results: Dict[str, List[Dict[str, Any]]] = {}
        self.errors: Dict[str, List[str]] = {}
    
    def test_function(
        self,
        function_name: str,
        params: Dict[str, Any] = None,
        iterations: int = 1,
        description: str = None
    ) -> Dict[str, Any]:
        """
        Тестирует RPC функцию и собирает статистику.
        
        Args:
            function_name: Имя RPC функции
            params: Параметры для функции
            iterations: Количество итераций
            description: Описание теста
        
        Returns:
            Словарь со статистикой выполнения
        """
        if params is None:
            params = {}
        
        if function_name not in self.results:
            self.results[function_name] = []
            self.errors[function_name] = []
        
        description = description or f"{function_name}({params})"
        print(f"\n{'='*80}")
        print(f"🧪 Тестирование: {description}")
        print(f"{'='*80}")
        
        times = []
        success_count = 0
        error_count = 0
        
        for i in range(iterations):
            try:
                start_time = time.perf_counter()
                
                # Вызываем RPC функцию
                # Для функций, возвращающих VOID, Supabase может вернуть пустой ответ
                try:
                    result = rpc(function_name, params)
                except ValueError as json_error:
                    # Если функция возвращает VOID (пустой ответ), это нормально
                    if "Expecting value" in str(json_error) or "char 0" in str(json_error):
                        result = None  # VOID функция успешно выполнена
                    else:
                        raise
                
                end_time = time.perf_counter()
                
                execution_time = end_time - start_time
                times.append(execution_time)
                success_count += 1
                
                # Сохраняем результат
                self.results[function_name].append({
                    'iteration': i + 1,
                    'time': execution_time,
                    'success': True,
                    'result_size': self._get_result_size(result),
                    'is_void': result is None,
                    'timestamp': datetime.now().isoformat()
                })
                
                result_info = " (VOID)" if result is None else ""
                print(f"  ✅ Итерация {i+1}/{iterations}: {execution_time:.3f}s{result_info}")
                
            except Exception as e:
                error_msg = str(e)
                error_count += 1
                self.errors[function_name].append(error_msg)
                self.results[function_name].append({
                    'iteration': i + 1,
                    'time': None,
                    'success': False,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
                print(f"  ❌ Итерация {i+1}/{iterations}: Ошибка - {error_msg}")
        
        # Статистика
        stats = {
            'function_name': function_name,
            'description': description,
            'iterations': iterations,
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': (success_count / iterations * 100) if iterations > 0 else 0,
        }
        
        if times:
            stats.update({
                'min_time': min(times),
                'max_time': max(times),
                'avg_time': statistics.mean(times),
                'median_time': statistics.median(times),
                'stdev_time': statistics.stdev(times) if len(times) > 1 else 0,
                'total_time': sum(times),
            })
        else:
            stats.update({
                'min_time': None,
                'max_time': None,
                'avg_time': None,
                'median_time': None,
                'stdev_time': None,
                'total_time': None,
            })
        
        return stats
    
    def _get_result_size(self, result: Any) -> int:
        """Оценивает размер результата."""
        if result is None:
            return 0
        if isinstance(result, (list, tuple)):
            return len(result)
        if isinstance(result, dict):
            return len(result)
        return 1
    
    def print_summary(self):
        """Выводит сводную статистику по всем тестам."""
        print(f"\n{'='*80}")
        print("📊 СВОДНАЯ СТАТИСТИКА")
        print(f"{'='*80}\n")
        
        if not self.results:
            print("Нет результатов для отображения.")
            return
        
        # Сортируем по среднему времени выполнения
        sorted_functions = sorted(
            self.results.items(),
            key=lambda x: self._get_avg_time(x[1]) or float('inf')
        )
        
        print(f"{'Функция':<40} {'Итераций':<10} {'Успешно':<10} {'Среднее':<12} {'Мин':<12} {'Макс':<12} {'Статус'}")
        print("-" * 110)
        
        for function_name, results in sorted_functions:
            success_results = [r for r in results if r.get('success')]
            times = [r['time'] for r in success_results if r.get('time') is not None]
            
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
            else:
                avg_time = min_time = max_time = None
            
            success_count = len(success_results)
            total_count = len(results)
            error_count = total_count - success_count
            
            status = "✅" if error_count == 0 else f"⚠️ {error_count} ошибок"
            
            avg_str = f"{avg_time:.3f}s" if avg_time else "N/A"
            min_str = f"{min_time:.3f}s" if min_time else "N/A"
            max_str = f"{max_time:.3f}s" if max_time else "N/A"
            
            print(f"{function_name:<40} {total_count:<10} {success_count:<10} {avg_str:<12} {min_str:<12} {max_str:<12} {status}")
        
        # Детальная статистика по ошибкам
        if any(self.errors.values()):
            print(f"\n{'='*80}")
            print("❌ ОШИБКИ")
            print(f"{'='*80}\n")
            for function_name, errors in self.errors.items():
                if errors:
                    print(f"  {function_name}:")
                    for error in set(errors):  # Уникальные ошибки
                        count = errors.count(error)
                        print(f"    - {error} (x{count})")
    
    def _get_avg_time(self, results: List[Dict]) -> Optional[float]:
        """Получает среднее время выполнения из результатов."""
        times = [r['time'] for r in results if r.get('success') and r.get('time') is not None]
        return statistics.mean(times) if times else None
    
    def export_to_json(self, filename: str = "rpc_test_results.json"):
        """Экспортирует результаты в JSON файл."""
        import json
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'results': self.results,
            'errors': self.errors,
            'summary': {}
        }
        
        # Добавляем сводку
        for function_name, results in self.results.items():
            success_results = [r for r in results if r.get('success')]
            times = [r['time'] for r in success_results if r.get('time') is not None]
            
            if times:
                export_data['summary'][function_name] = {
                    'total_iterations': len(results),
                    'success_count': len(success_results),
                    'error_count': len(results) - len(success_results),
                    'min_time': min(times),
                    'max_time': max(times),
                    'avg_time': statistics.mean(times),
                    'median_time': statistics.median(times),
                    'stdev_time': statistics.stdev(times) if len(times) > 1 else 0,
                }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Результаты экспортированы в {filename}")


def get_test_functions() -> Dict[str, Dict[str, Any]]:
    """Возвращает список функций для тестирования с их параметрами."""
    
    # Получаем реальные данные из БД для тестирования
    asset_ids = [1]
    portfolio_ids = [1]
    user_id = None
    
    try:
        assets = table_select("assets", "id", limit=10)
        if assets:
            asset_ids = [a["id"] for a in assets]
        
        portfolios = table_select("portfolios", "id", limit=5)
        if portfolios:
            portfolio_ids = [p["id"] for p in portfolios]
        
        users = table_select("users", "id", filters={"name": 'Администратор'})
        if users:
            user_id = users[0]["id"]
        
        print(f"📊 Загружено данных: {len(asset_ids)} активов, {len(portfolio_ids)} портфелей")
        
    except Exception as e:
        print(f"⚠️ Не удалось получить данные из БД: {e}")
        print("   Используются значения по умолчанию")
    
    return {
        'refresh_asset_latest_prices': {
            'params': {},
            'description': 'Полное обновление цен всех активов',
            'iterations': 1,  # Обычно долгая операция
        },
        'update_asset_latest_price': {
            'params': {'p_asset_id': asset_ids[0] if asset_ids else 1},
            'description': 'Обновление цены одного актива',
            'iterations': 3,
        },
        'update_asset_latest_prices_batch': {
            'params': {'p_asset_ids': asset_ids[:10] if len(asset_ids) >= 10 else asset_ids},
            'description': 'Обновление цен батчем (10 активов)',
            'iterations': 2,
        },
        'get_reference_data': {
            'params': {},
            'description': 'Получение справочных данных',
            'iterations': 3,
        },
        'get_portfolio_assets': {
            'params': {'p_portfolio_id': portfolio_ids[0] if portfolio_ids else 1},
            'description': 'Получение активов портфеля',
            'iterations': 3,
        },
        'get_portfolio_analytics': {
            'params': {
                'p_portfolio_id': portfolio_ids[0] if portfolio_ids else 1,
                'p_user_id': user_id
            } if user_id else {'p_portfolio_id': portfolio_ids[0] if portfolio_ids else 1},
            'description': 'Получение аналитики портфеля',
            'iterations': 2,
            'skip_if_no_params': True,  # Требует user_id
        },
        'get_user_portfolios': {
            'params': {'u_id': user_id} if user_id else {},
            'description': 'Получение портфелей пользователя',
            'iterations': 3,
            'skip_if_no_params': True,
        },
        'refresh_all_portfolio_daily_data': {
            'params': {},
            'description': 'Обновление всех портфельных данных',
            'iterations': 1,  # Обычно долгая операция
        },
    }


def test_batch_sizes(tester: RPCTester, base_asset_ids: List[int]):
    """Тестирует функцию с разными размерами батчей."""
    print(f"\n{'='*80}")
    print("📦 ТЕСТИРОВАНИЕ РАЗНЫХ РАЗМЕРОВ БАТЧЕЙ")
    print(f"{'='*80}\n")
    
    batch_sizes = [10, 50, 100, 500, 1000]
    
    for batch_size in batch_sizes:
        if len(base_asset_ids) < batch_size:
            print(f"⚠️ Пропуск батча {batch_size} (недостаточно активов)")
            continue
        
        batch_ids = base_asset_ids[:batch_size]
        tester.test_function(
            'update_asset_latest_prices_batch',
            params={'p_asset_ids': batch_ids},
            iterations=1,
            description=f'Батч из {batch_size} активов'
        )


def main():
    parser = argparse.ArgumentParser(description='Тестирование RPC функций с аналитикой')
    parser.add_argument(
        '--function',
        type=str,
        help='Тестировать только указанную функцию'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=1,
        help='Количество итераций для каждой функции (по умолчанию: 1)'
    )
    parser.add_argument(
        '--batch-size',
        action='store_true',
        help='Тестировать разные размеры батчей'
    )
    parser.add_argument(
        '--export',
        type=str,
        help='Экспортировать результаты в JSON файл'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Тестировать все функции'
    )
    
    args = parser.parse_args()
    
    tester = RPCTester()
    test_functions = get_test_functions()
    
    print("🚀 Запуск тестирования RPC функций")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if args.function:
        # Тестируем только указанную функцию
        if args.function in test_functions:
            func_config = test_functions[args.function]
            tester.test_function(
                args.function,
                params=func_config['params'],
                iterations=args.iterations or func_config.get('iterations', 1),
                description=func_config.get('description')
            )
        else:
            print(f"❌ Функция '{args.function}' не найдена в списке тестовых функций")
            print(f"Доступные функции: {', '.join(test_functions.keys())}")
            return
    elif args.batch_size:
        # Тестируем разные размеры батчей
        try:
            assets = table_select("assets", "id", limit=1000)
            asset_ids = [a["id"] for a in assets] if assets else []
            test_batch_sizes(tester, asset_ids)
        except Exception as e:
            print(f"❌ Ошибка при получении активов: {e}")
    else:
        # Тестируем все функции или выбранные
        for function_name, func_config in test_functions.items():
            # Пропускаем функции, требующие параметры, если их нет
            if func_config.get('skip_if_no_params') and not func_config['params']:
                print(f"⏭️ Пропуск {function_name} (нет необходимых параметров)")
                continue
            
            tester.test_function(
                function_name,
                params=func_config['params'],
                iterations=args.iterations or func_config.get('iterations', 1),
                description=func_config.get('description')
            )
    
    # Выводим сводку
    tester.print_summary()
    
    # Экспортируем результаты, если указано
    if args.export:
        tester.export_to_json(args.export)
    elif args.all or args.function or args.batch_size:
        # Автоматически экспортируем при тестировании
        tester.export_to_json()
    
    print(f"\n✅ Тестирование завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

