"""
Pydantic модели для операций по активам.
Поддерживает все типы операций: Buy, Sell, Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Redemption, Other.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union, List
from datetime import datetime


class CreateOperationRequest(BaseModel):
    """Модель запроса создания операции по активу."""
    portfolio_asset_id: Optional[int] = Field(None, ge=1, description="ID портфельного актива (обязателен для Buy/Sell)")
    asset_id: Optional[int] = Field(None, ge=1, description="ID актива (обязателен для Buy/Sell/Dividend/Coupon, опционален для Commission/Tax)")
    portfolio_id: Optional[int] = Field(None, ge=1, description="ID портфеля (опционален, если передан portfolio_asset_id)")
    operation_type: Union[int, str] = Field(..., description="Тип операции: 1=Buy, 2=Sell, 3=Dividend, 4=Coupon, 5=Deposit, 6=Withdraw, 7=Commission, 8=Tax, 9=Redemption, 10=Other")
    amount: float = Field(..., description="Сумма операции (положительная для доходов, отрицательная для расходов)")
    currency_id: Optional[int] = Field(1, description="ID валюты (по умолчанию RUB=1)")
    operation_date: Union[datetime, str] = Field(..., description="Дата операции")
    
    # Поля для Buy/Sell транзакций
    quantity: Optional[float] = Field(None, gt=0, description="Количество (обязательно для Buy/Sell)")
    price: Optional[float] = Field(None, gt=0, description="Цена за единицу (обязательно для Buy/Sell)")
    
    # Поля для выплат (Dividend/Coupon)
    dividend_yield: Optional[float] = Field(None, description="Дивидендная доходность (для Dividend/Coupon, опционально, рассчитывается автоматически)")
    
    # Флаг для создания операции пополнения
    create_deposit_operation: bool = Field(False, description="Создать операцию пополнения для комиссии/налога (только для operation_type=7 или 8)")
    
    @field_validator('operation_type', mode='before')
    @classmethod
    def parse_operation_type(cls, v):
        """Преобразует тип операции в число."""
        type_map = {
            'buy': 1, 'покупка': 1, '1': 1,
            'sell': 2, 'продажа': 2, '2': 2,
            'dividend': 3, 'дивиденд': 3, 'дивиденды': 3, '3': 3,
            'coupon': 4, 'купон': 4, 'купоны': 4, '4': 4,
            'deposit': 5, 'депозит': 5, 'пополнение': 5, '5': 5,
            'withdraw': 6, 'вывод': 6, 'снятие': 6, '6': 6,
            'commission': 7, 'комиссия': 7, '7': 7,
            'tax': 8, 'налог': 8, 'налоги': 8, '8': 8,
            'redemption': 9, 'ammortization': 9, 'амортизация': 9, 'погашение': 9, '9': 9,
            'other': 10, 'другое': 10, 'прочее': 10, '10': 10
        }
        
        if isinstance(v, int):
            if 1 <= v <= 10:
                return v
            raise ValueError(f"operation_type должен быть от 1 до 10, получен: {v}")
        
        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower in type_map:
                return type_map[v_lower]
            raise ValueError(f"Некорректный тип операции: {v}. Ожидается: Buy, Sell, Dividend, Coupon, Deposit, Withdraw, Commission, Tax, Redemption, Other")
        
        raise ValueError(f"operation_type должен быть строкой или числом, получен: {type(v)}")
    
    @field_validator('operation_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Парсит дату из строки или datetime."""
        if isinstance(v, str):
            try:
                if 'T' in v:
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(v)
            except:
                return v
        return v
    
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v, info):
        """Валидация суммы операции."""
        if v == 0:
            raise ValueError("amount не может быть равен нулю")
        return v
    
    def model_post_init(self, __context):
        """Дополнительная валидация в зависимости от типа операции."""
        op_type = self.operation_type if isinstance(self.operation_type, int) else int(self.operation_type)
        
        # Проверяем, что передан либо portfolio_id, либо portfolio_asset_id
        if not self.portfolio_id and not self.portfolio_asset_id:
            raise ValueError("Необходимо указать либо portfolio_id, либо portfolio_asset_id")
        
        # Buy/Sell/Redemption требуют portfolio_asset_id, asset_id, quantity, price
        if op_type in [1, 2, 9]:
            if not self.portfolio_asset_id:
                raise ValueError("portfolio_asset_id обязателен для Buy/Sell")
            if not self.asset_id:
                raise ValueError("asset_id обязателен для Buy/Sell")
            if not self.quantity:
                raise ValueError("quantity обязателен для Buy/Sell")
            if not self.price:
                raise ValueError("price обязателен для Buy/Sell")
        
        # Dividend/Coupon требуют asset_id
        if op_type in [3, 4]:
            if not self.asset_id:
                raise ValueError("asset_id обязателен для Dividend/Coupon")
        
        # Deposit/Withdraw требуют portfolio_id
        if op_type in [5, 6]:
            if not self.portfolio_id and not self.portfolio_asset_id:
                raise ValueError("portfolio_id обязателен для Deposit/Withdraw")
        
        # Commission/Tax могут иметь asset_id (опционально)


class BatchCreateOperationRequest(BaseModel):
    """Модель запроса массового создания операций (повторяющиеся операции)."""
    portfolio_asset_id: Optional[int] = Field(None, ge=1, description="ID портфельного актива (обязателен для Buy/Sell)")
    asset_id: Optional[int] = Field(None, ge=1, description="ID актива (обязателен для Buy/Sell/Dividend/Coupon, опционален для Commission/Tax)")
    portfolio_id: Optional[int] = Field(None, ge=1, description="ID портфеля (опционален, если передан portfolio_asset_id)")
    operation_type: Union[int, str] = Field(..., description="Тип операции: 1=Buy, 2=Sell, 3=Dividend, 4=Coupon, 5=Deposit, 6=Withdraw, 7=Commission, 8=Tax, 9=Redemption, 10=Other")
    amount: float = Field(..., description="Сумма операции (положительная для доходов, отрицательная для расходов)")
    currency_id: Optional[int] = Field(1, description="ID валюты (по умолчанию RUB=1)")
    start_date: Union[datetime, str] = Field(..., description="Дата начала повторения")
    end_date: Union[datetime, str] = Field(..., description="Дата окончания повторения")
    day_of_month: int = Field(..., ge=1, le=31, description="День месяца для создания операции (1-31)")
    
    # Поля для Buy/Sell транзакций
    quantity: Optional[float] = Field(None, gt=0, description="Количество (обязательно для Buy/Sell)")
    price: Optional[float] = Field(None, gt=0, description="Цена за единицу (обязательно для Buy/Sell)")
    
    # Поля для выплат (Dividend/Coupon)
    dividend_yield: Optional[float] = Field(None, description="Дивидендная доходность (для Dividend/Coupon, опционально)")
    
    @field_validator('operation_type', mode='before')
    @classmethod
    def parse_operation_type(cls, v):
        """Преобразует тип операции в число."""
        type_map = {
            'buy': 1, 'покупка': 1, '1': 1,
            'sell': 2, 'продажа': 2, '2': 2,
            'dividend': 3, 'дивиденд': 3, 'дивиденды': 3, '3': 3,
            'coupon': 4, 'купон': 4, 'купоны': 4, '4': 4,
            'deposit': 5, 'депозит': 5, 'пополнение': 5, '5': 5,
            'withdraw': 6, 'вывод': 6, 'снятие': 6, '6': 6,
            'commission': 7, 'комиссия': 7, '7': 7,
            'tax': 8, 'налог': 8, 'налоги': 8, '8': 8,
            'redemption': 9, 'погашение': 9, '9': 9,
            'other': 10, 'другое': 10, 'прочее': 10, '10': 10
        }
        
        if isinstance(v, int):
            if 1 <= v <= 10:
                return v
            raise ValueError(f"operation_type должен быть от 1 до 10, получен: {v}")
        
        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower in type_map:
                return type_map[v_lower]
            raise ValueError(f"Некорректный тип операции: {v}")
        
        raise ValueError(f"operation_type должен быть строкой или числом, получен: {type(v)}")
    
    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Парсит дату из строки или datetime."""
        if isinstance(v, str):
            try:
                if 'T' in v:
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(v)
            except:
                return v
        return v
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Валидация суммы операции."""
        if v == 0:
            raise ValueError("amount не может быть равен нулю")
        return v
    
    def model_post_init(self, __context):
        """Дополнительная валидация."""
        op_type = self.operation_type if isinstance(self.operation_type, int) else int(self.operation_type)
        
        # Проверяем, что передан либо portfolio_id, либо portfolio_asset_id
        if not self.portfolio_id and not self.portfolio_asset_id:
            raise ValueError("Необходимо указать либо portfolio_id, либо portfolio_asset_id")
        
        # Проверяем, что end_date >= start_date
        start = self.start_date if isinstance(self.start_date, datetime) else datetime.fromisoformat(str(self.start_date))
        end = self.end_date if isinstance(self.end_date, datetime) else datetime.fromisoformat(str(self.end_date))
        if end < start:
            raise ValueError("end_date должна быть позже или равна start_date")
        
        # Buy/Sell/Redemption требуют portfolio_asset_id, asset_id, quantity, price
        if op_type in [1, 2, 9]:
            if not self.portfolio_asset_id:
                raise ValueError("portfolio_asset_id обязателен для Buy/Sell")
            if not self.asset_id:
                raise ValueError("asset_id обязателен для Buy/Sell")
            if not self.quantity:
                raise ValueError("quantity обязателен для Buy/Sell")
            if not self.price:
                raise ValueError("price обязателен для Buy/Sell")
        
        # Dividend/Coupon требуют asset_id
        if op_type in [3, 4]:
            if not self.asset_id:
                raise ValueError("asset_id обязателен для Dividend/Coupon")


class UpdateOperationRequest(BaseModel):
    """Модель запроса обновления операции (дата и/или сумма). Для синхронизации операции пополнения при редактировании транзакции."""
    operation_date: Optional[str] = Field(None, description="Новая дата операции")
    amount: Optional[float] = Field(None, description="Новая сумма операции")


class UpdateOperationItem(BaseModel):
    """Один элемент батчевого обновления операций."""
    operation_id: int = Field(..., description="ID операции")
    operation_date: Optional[str] = Field(None, description="Новая дата операции")
    amount: Optional[float] = Field(None, description="Новая сумма операции")
    quantity: Optional[float] = Field(None, description="Новое количество (для buy/sell/redemption, если нужно)")
    price: Optional[float] = Field(None, description="Новая цена за единицу (для buy/sell/redemption, если нужно)")


class UpdateOperationsBatchRequest(BaseModel):
    """Модель запроса батчевого обновления операций."""
    updates: List[UpdateOperationItem] = Field(..., min_length=1, description="Список обновлений")


class DeleteOperationsRequest(BaseModel):
    """Модель запроса удаления операций (batch)."""
    ids: List[int] = Field(..., min_length=1, description="Список ID операций для удаления")


class ApplyOperationItem(BaseModel):
    """
    Единый формат элемента для apply-эндпоинта.
    Сервер преобразует элементы в формат, который понимает SQL `apply_operations_batch`.
    """

    operation_type: int = Field(..., ge=1, le=10, description="ID типа операции (1..10 как в operations_type)")
    operation_date: Union[datetime, str] = Field(..., description="Дата операции")

    # Общие поля
    portfolio_id: Optional[int] = Field(None, ge=1, description="ID портфеля (может быть выведен из portfolio_asset_id)")
    portfolio_asset_id: Optional[int] = Field(None, ge=1, description="ID portfolio_asset (для buy/sell/redemption и для привязки cash-операций)")
    asset_id: Optional[int] = Field(None, ge=1, description="ID актива (для buy/sell/redemption и для dividend/coupon)")

    # Cash-поля
    amount: Optional[float] = Field(None, description="Сумма cash-операции (для buy/sell/redemption будет вычислена)")
    currency_id: Optional[int] = Field(1, ge=1, description="ID валюты для cash-операций")
    dividend_yield: Optional[float] = Field(None, description="Не используется в расчетах прямо сейчас, но передается для совместимости")

    # Transaction-поля
    quantity: Optional[float] = Field(None, gt=0, description="Количество для buy/sell/redemption")
    price: Optional[float] = Field(None, gt=0, description="Цена за единицу для buy/sell/redemption")

    # Автоматически создает Deposit-операцию в этом же apply-запросе
    create_deposit_operation: bool = Field(
        False,
        description="Создать операцию пополнения в этом же запросе (для Buy и для Commission/Tax).",
    )

    @field_validator("operation_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        """Парсит дату из строки или datetime."""
        if isinstance(v, str):
            try:
                if "T" in v:
                    return datetime.fromisoformat(v.replace("Z", "+00:00"))
                return datetime.fromisoformat(v)
            except:
                return v
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount_not_zero(cls, v):
        if v is None:
            return v
        if float(v) == 0:
            raise ValueError("amount не может быть равен нулю")
        return v

    def operation_category(self) -> str:
        """Упрощенная классификация для преобразования payload."""
        if self.operation_type in (1, 2, 9):
            return "transaction"
        return "cash"


class ApplyOperationsRequest(BaseModel):
    """
    Запрос на создание произвольного набора операций одним SQL-вызовом.
    """

    operations: List[ApplyOperationItem] = Field(..., min_length=1)