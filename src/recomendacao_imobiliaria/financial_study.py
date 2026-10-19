"""Preliminary, unlevered sale-development cash flow from declared assumptions."""
from datetime import date
from pydantic import BaseModel, ConfigDict, Field


class FinancialInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    land_cost: float | None = Field(None, ge=0, le=1e12)
    construction_cost_m2: float | None = Field(None, gt=0, le=1e7)
    other_costs: float | None = Field(None, ge=0, le=1e12)
    contingency_pct: float | None = Field(None, ge=0, le=100)
    saleable_area_m2: float | None = Field(None, ge=.01, le=1e8)
    sale_price_m2: float | None = Field(None, gt=0, le=1e9)
    sales_expenses_pct: float | None = Field(None, ge=0, le=100)
    months: int | None = Field(None, ge=1, le=600)
    annual_discount_pct: float | None = Field(None, ge=0, le=100)
    cost_variation_pct: float | None = Field(None, ge=0, le=100)
    price_variation_pct: float | None = Field(None, ge=0, le=100)
    reference_date: date | None = None
    source_note: str = Field('', max_length=4000)


LIMITATIONS = [
    'Valores em reais nominais, informados pelo usuário e não verificados como cotações de mercado.',
    'Modelo de venda integral no último mês, sem financiamento, pré-vendas, inflação ou tributação automática. Incluir despesas e tributos estimados nas premissas, sem duplicá-los.',
    'Terreno pago no mês zero; construção e contingência distribuídas igualmente ao longo do prazo; outros custos no mês um. Despesas de venda descontadas da receita na entrega.',
    'VPL calculado com taxa mensal equivalente à taxa anual informada. ROI e margem correspondem ao empreendimento inteiro, não são taxas anuais.',
    'Sensibilidade altera apenas custo unitário de construção e preço de venda. Não representa probabilidade ou previsão de mercado.',
    'Déficit máximo é apurado pelo saldo líquido de cada mês; desembolsos e recebimentos dentro do mesmo mês não são ordenados.',
    'Montantes arredondados a centavos; diferenças de rateio são distribuídas entre as parcelas mensais.',
    'Resultados financeiros não comprovam aprovação urbanística ou viabilidade técnica e não garantem retorno.',
]


def evaluate_financial(raw, build_area):
    if raw is None:
        return {'status': 'not_requested', 'methodology': 'sale_cashflow_v1', 'limitations': LIMITATIONS}
    assumptions = FinancialInput.model_validate(raw)
    missing = [key for key, value in assumptions.model_dump().items() if value is None or (key == 'source_note' and not value.strip())]
    result = {'status': 'pending' if missing else 'complete', 'methodology': 'sale_cashflow_v1',
              'currency': 'BRL', 'missing': missing, 'assumptions': assumptions.model_dump(mode='json'),
              'build_area_m2': build_area, 'limitations': LIMITATIONS}
    if missing:
        return result
    scenarios = []
    monthly_rate = (1 + assumptions.annual_discount_pct / 100) ** (1 / 12) - 1
    for key, label, cost_factor, price_factor in [
        ('base', 'Base informado', 1, 1),
        ('stress', 'Pressão de custos e vendas', 1 + assumptions.cost_variation_pct / 100, 1 - assumptions.price_variation_pct / 100),
        ('favorable', 'Alívio de custos e vendas', 1 - assumptions.cost_variation_pct / 100, 1 + assumptions.price_variation_pct / 100),
    ]:
        construction = round(build_area * assumptions.construction_cost_m2 * cost_factor, 2)
        land_cost, other_costs = round(assumptions.land_cost, 2), round(assumptions.other_costs, 2)
        contingency = round(construction * assumptions.contingency_pct / 100, 2)
        total = round(land_cost + construction + contingency + other_costs, 2)
        gross = round(assumptions.saleable_area_m2 * assumptions.sale_price_m2 * price_factor, 2)
        sales_expenses = round(gross * assumptions.sales_expenses_pct / 100, 2)
        net = round(gross - sales_expenses, 2)
        profit = round(net - total, 2)
        cumulative = -land_cost
        npv = cumulative
        minimum = cumulative
        flows = [{'month': 0, 'cost': round(assumptions.land_cost, 2), 'revenue': 0, 'net': round(cumulative, 2), 'cumulative': round(cumulative, 2)}]
        for month in range(1, assumptions.months + 1):
            cost = round(round((construction + contingency) * month / assumptions.months, 2) - round((construction + contingency) * (month - 1) / assumptions.months, 2) + (other_costs if month == 1 else 0), 2)
            revenue = net if month == assumptions.months else 0
            cash = round(revenue - cost, 2)
            cumulative = round(cumulative + cash, 2)
            minimum = min(minimum, cumulative)
            npv += cash / ((1 + monthly_rate) ** month)
            flows.append({'month': month, 'cost': round(cost, 2), 'revenue': round(revenue, 2), 'net': round(cash, 2), 'cumulative': round(cumulative, 2)})
        denominator = assumptions.saleable_area_m2 * (1 - assumptions.sales_expenses_pct / 100)
        scenarios.append({
            'id': key, 'label': label, 'construction_cost': round(construction, 2), 'contingency': round(contingency, 2),
            'total_cost': round(total, 2), 'gross_revenue': round(gross, 2), 'sales_expenses': round(sales_expenses, 2),
            'net_revenue': round(net, 2), 'profit': round(profit, 2), 'npv': round(npv, 2),
            'margin_pct': round(profit / gross * 100, 2) if gross else None,
            'roi_pct': round(profit / total * 100, 2) if total else None,
            'break_even_price_m2': round(total / denominator, 2) if denominator else None,
            'peak_monthly_deficit': round(max(0, -minimum), 2), 'cash_flow': flows,
        })
    result['scenarios'] = scenarios
    return result
