# Frugal для enterprise — token-tax это уже реальные деньги

**[🇬🇧 English](ENTERPRISE.md)**

Если гоняешь агентов в масштабе, инференс — уже не строка расходов, а сам счёт. Frugal — слой контроля:
маршрутизирует большую часть на дешёвую/локальную модель, доказывает, что качество не упало, и режет
спенд. Кейс с реальными, цитируемыми числами.

## Кто это жжёт — ростер 2026

| Компания | Факт 2026 | Источник |
|---|---|---|
| **Meta** | AI-capex поднят до **$125–145B**; ~$25B/квартал уже уходит на «короткоживущий» **инференс**-кремний | [Krasa](https://www.krasa.ai/news/meta-2026-ai-capex-145-billion-infrastructure-bet) |
| **Amazon** | ~**$200B** AI-capex 2026; Bedrock хостит Anthropic + Grok | [ValueAdd](https://valueaddvc.com/ai-spending) |
| **Google** | Gemini отдаёт **1.3 квадриллиона токенов / месяц** | [Statista/Krasa](https://www.krasa.ai/news/meta-2026-ai-capex-145-billion-infrastructure-bet) |
| **Microsoft** | ~$120B capex; **GitHub Copilot перешёл на токен-биллинг** (июнь 2026, «meter shock») | [Windows Forum](https://windowsforum.com/threads/copilot-to-usage-billing-june-1-2026-ai-credits-token-costs-and-meter-shock.420900/) |
| **xAI** | Anthropic платит xAI **$1.25B/месяц** за Colossus; **>1M API-вызовов/день** | [Enterprise DNA](https://enterprisedna.co/resources/news/anthropic-xai-colossus-1-25-billion-compute-economics-2026/) |
| **Palantir** | CEO: token-pricing **«полностью сломан»** → Palantir+Nvidia делают **air-gapped, без hosted API** | [TechTimes](https://www.techtimes.com/articles/319702/20260704/palantir-nvidia-launch-air-gapped-ai-stack-token-billing-cracks-enterprise-budgets.htm) |
| **Oracle** | OCI Enterprise AI; хостит Palantir Foundry/AIP | [Oracle](https://docs.oracle.com/en/solutions/palantir-foundry-ai-platform-on-oci/index.html) |
| **Salesforce** | Из-за взрыва цен — Agentforce **resolution-based** прайсинг, кредиты $0.10/действие | [BigGo](https://finance.biggo.com/news/d50e3253-faf4-4f76-b5f9-18134d747e5e) |
| **Uber** | **Спалил весь AI-coding бюджет 2026 к апрелю** (использование 32% → 84% за 3 мес) | [CNBC](https://www.cnbc.com/2026/06/26/openai-anthropic-new-ai-spending-reality-as-users-shift-to-efficiency.html) |
| **Klarna** | AI-ассистент: **2.3M диалогов/месяц**, работа ~850 агентов | [Klarna](https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/) |
| **Fortune-500 фирма** | **$500M на Claude за один месяц** — без бюджет-cap | [Optimum](https://optimumpartners.com/insight/ai-token-costs-and-how-they-might-wreck-your-budget/) |
| **Отрасль** | Enterprise LLM-спенд **$8.4B → удвоение**; **инференс = 85% AI-бюджета**; рынок $66B→$292B к 2029 | [Oplexa](https://oplexa.com/ai-inference-cost-crisis-2026/) |

Цены на токены упали ~280× за два года, но общий спенд **вырос ~320%** — из-за агентного объёма.
**Дешёвые токены не спасают. Спасает роутинг того, чему не нужна большая модель.** CEO Palantir уже
говорит это вслух — и толкает ровно тот local-first / on-prem путь, под который создан Frugal.

## Сколько Frugal экономит, по месячному спенду

Frugal отправляет вызовы, которым не нужна frontier-модель, на дешёвую/локальную и эскалирует только
при провале проверки — экономит **~50–75% маршрутизируемого спенда** (замеряем 75–91% на дешёвой доле;
диапазон нарочно консервативный). Моделируется — `python benchmarks/cost_model.py`:

| Месячный спенд | Frugal экономит / мес | Frugal экономит / год |
|---|---|---|
| $100,000 | **$50k – $75k** | $0.6M – $0.9M |
| $1,000,000 | **$0.5M – $0.75M** | $6M – $9M |
| $10,000,000 | **$5M – $7.5M** | $60M – $90M |
| $50,000,000 (Fortune-500) | **$25M – $37.5M** | $300M – $450M |

## Ситуации, под которые Frugal и создан

- **«Uber спалил бюджет к апрелю».** Потокобезопасный **бюджет-cap** + `reserve()` (отказ до траты) →
  бюджет нельзя спалить молча; роутинг растягивает его в 2–4×.
- **«$500M на Claude за месяц без cap».** Ровно это предотвращает бюджет-gateway — cap и живой $/token
  на каждый ключ/тенант (MCP-сервер).
- **Palantir «air-gapped, без hosted API».** Local-first роутинг держит приватное/простое на своих GPU
  (0 утечек) и эскалирует на hosted frontier только при реальной нужде.
- **Klarna-масштаб (2.3M чатов/мес ≈ 6.9M вызовов).** Модельная экономия токенов ≈ **$210k/год**.
- **Кодинг-агенты (паттерн Uber/Copilot).** Тривиальные правки → дёшево; reasoning → frontier.

## Почему роутить безопасно

Мы **замерили**: LLM-судья признал 3B **не хуже** 14B на **83% сложных задач (100% простых)**; остальное
Frugal эскалирует. И публикуем, где роутинг **НЕ** окупается. Детали:
[BUSINESS_CASE.md](BUSINESS_CASE.md) · [WEAKNESSES.md](WEAKNESSES.md).

## Для пилота

Направь base-url одной нагрузки на Frugal-gateway, поставь бюджет, оставь свои модели. Померь за неделю.
→ **razikovsardor1@gmail.com** · [github.com/SRKRZ23/frugal](https://github.com/SRKRZ23/frugal)

*Числа экономии моделируются на публичных ценах 2026 и консервативной доле маршрутизируемого. Факты о
компаниях — цитируемые публичные отчёты; Frugal не аффилирован и не одобрен упомянутыми компаниями.*
