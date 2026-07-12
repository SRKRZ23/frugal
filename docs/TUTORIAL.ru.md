# Туториал Frugal — от нуля до cost-роутинга за 10 минут

**[🇬🇧 English](TUTORIAL.md) · 🇷🇺 Русский**

Каждый шаг сначала работает офлайн (mock-провайдер), потом показан переход на реальные модели.

## 0. Установка
```bash
git clone https://github.com/SRKRZ23/frugal && cd frugal
pip install -e .
frugal demo            # офлайн-демо, ~2с, без ключей
```

## 1. Считай вызов (знай, сколько потратил)
```python
from frugal import Meter, MockProvider
meter, prov = Meter(), MockProvider()
with meter.track("gpt-4o-mini") as call:
    call.set(prov.complete("суммаризируй это", model="gpt-4o-mini"))
print(meter.summary())          # стоимость, токены, разбивка по моделям
```

## 2. Cost-роутинг (сначала дешёвая, эскалация при необходимости)
```python
from frugal import cascade
r = cascade("привет", prov, meter)                       # остаётся на дешёвой
r = cascade("докажи дизайн по шагам", prov, meter)       # эскалирует
print(r.model_used, r.escalated)
```

## 3. Реальный сигнал уверенности (работает на реальных моделях)
```python
from frugal.route import make_logprob_confidence   # почти бесплатный
conf = make_logprob_confidence()
r = cascade(prompt, prov, meter, ladder=["gpt-4o-mini", "gpt-4o"], confidence_fn=conf)
# Frugal предупредит, если пара cheap/frontier не окупит роутинг.
```

## 4. Жёсткий бюджет
```python
from frugal.meter import BudgetExceeded
meter = Meter(budget_usd=5.00, max_history=1000)   # cap + bounded-память
try:
    for job in jobs:
        cascade(job, prov, meter)
except BudgetExceeded:
    print("остановлено на лимите — без сюрприз-счёта")
```

## 5. Гейт качества в CI (ловим тихие регрессии)
```python
from frugal.eval import assert_semantic, assert_no_hallucination
def test_answer():
    out = my_agent("столица Франции?")
    assert_semantic(out, "Париж — столица Франции", threshold=0.4)
    assert_no_hallucination(out, context=retrieved_docs)
```

## 6. Реальные модели (cloud или local)
```python
from frugal.providers import get_openai, get_ollama
cloud = get_openai(base_url="https://api.openai.com/v1")     # любой OpenAI-совместимый
local = get_ollama(model="llama3")                           # http://localhost:11434
```

## 7. Кэш ответов (второй рычаг экономии)
```python
from frugal import ResponseCache
cache = ResponseCache(normalize=True)
cascade(prompt, prov, meter, cache=cache)   # повтор промпта = $0
```

## 8. OpenAI-совместимый бюджет-gateway
```bash
pip install 'frugal[gateway]'
frugal gateway --budget 5.00          # направь любой OpenAI-SDK на http://localhost:8080
```

## 9. Докажи экономию для СВОЕЙ конфигурации
```bash
python benchmarks/cost_model.py       # правь PRICES / токены / смесь -> твоя экономия
python benchmarks/bench_models.py      # сравни свои модели (нужен Ollama/кластер)
```

Весь цикл: **считай → маршрутизируй → проверяй → (бюджет) → деплой**, дёшево и локально по умолчанию.
