# ================================================
# valuation_ddm.py
# Dividend Discount Model para tu sistema
# ================================================
from Modulos_python import np


class DividendDiscountModel:
    """
    Implementa múltiples variantes del DDM:
    - Gordon Growth Model (crecimiento constante)
    - Two-Stage DDM
    - Three-Stage DDM
    """

    def __init__(self, current_dividend_per_share, required_return):
        """
        current_dividend_per_share: Dividendo anual por acción actual
        required_return: Tasa de retorno requerida (ej: 0.10 = 10%)
        """
        self.D0 = current_dividend_per_share
        self.r = required_return

    def gordon_growth(self, growth_rate):
        """
        Gordon Growth Model (GGM)
        Valor Intrínseco = D1 / (r - g)

        D1 = Dividendo año próximo = D0 * (1 + g)
        r = Tasa de retorno requerida
        g = Tasa de crecimiento perpetuo del dividendo
        """
        if growth_rate >= self.r:
            return {
                "error": "Tasa de crecimiento debe ser menor que tasa de retorno",
                "intrinsic_value": None,
            }

        D1 = self.D0 * (1 + growth_rate)
        intrinsic_value = D1 / (self.r - growth_rate)

        return {
            "model": "Gordon Growth Model",
            "D0": self.D0,
            "D1": D1,
            "growth_rate": growth_rate,
            "required_return": self.r,
            "intrinsic_value": intrinsic_value,
        }

    def two_stage(self, high_growth_rate, high_growth_years, stable_growth_rate):
        """
        Two-Stage DDM
        Fase 1: Crecimiento alto por N años
        Fase 2: Crecimiento estable perpetuo
        """
        if stable_growth_rate >= self.r:
            return {
                "error": "Tasa de crecimiento estable debe ser menor que tasa de retorno",
                "intrinsic_value": None,
            }

        # Fase 1: Valor presente de dividendos en crecimiento alto
        pv_stage1 = 0
        D = self.D0

        for year in range(1, high_growth_years + 1):
            D = D * (1 + high_growth_rate)
            pv = D / ((1 + self.r) ** year)
            pv_stage1 += pv

        # Fase 2: Valor terminal con Gordon Growth
        D_terminal = D * (1 + stable_growth_rate)
        terminal_value = D_terminal / (self.r - stable_growth_rate)
        pv_terminal = terminal_value / ((1 + self.r) ** high_growth_years)

        intrinsic_value = pv_stage1 + pv_terminal

        return {
            "model": "Two-Stage DDM",
            "D0": self.D0,
            "high_growth_rate": high_growth_rate,
            "high_growth_years": high_growth_years,
            "stable_growth_rate": stable_growth_rate,
            "required_return": self.r,
            "pv_stage1": pv_stage1,
            "pv_terminal": pv_terminal,
            "intrinsic_value": intrinsic_value,
        }

    def three_stage(
        self,
        high_growth_rate,
        high_growth_years,
        transition_years,
        stable_growth_rate,
    ):
        """
        Three-Stage DDM
        Fase 1: Crecimiento alto
        Fase 2: Transición lineal de crecimiento alto a estable
        Fase 3: Crecimiento estable perpetuo
        """
        if stable_growth_rate >= self.r:
            return {
                "error": "Tasa de crecimiento estable debe ser menor que tasa de retorno",
                "intrinsic_value": None,
            }

        pv_total = 0
        D = self.D0
        year = 0

        # Fase 1: Alto crecimiento
        for _ in range(high_growth_years):
            year += 1
            D = D * (1 + high_growth_rate)
            pv_total += D / ((1 + self.r) ** year)

        # Fase 2: Transición (declinación lineal)
        growth_decline = (high_growth_rate - stable_growth_rate) / transition_years

        for i in range(transition_years):
            year += 1
            current_growth = high_growth_rate - (growth_decline * (i + 1))
            D = D * (1 + current_growth)
            pv_total += D / ((1 + self.r) ** year)

        # Fase 3: Crecimiento estable (valor terminal)
        D_terminal = D * (1 + stable_growth_rate)
        terminal_value = D_terminal / (self.r - stable_growth_rate)
        pv_terminal = terminal_value / ((1 + self.r) ** year)

        intrinsic_value = pv_total + pv_terminal

        return {
            "model": "Three-Stage DDM",
            "D0": self.D0,
            "high_growth_rate": high_growth_rate,
            "high_growth_years": high_growth_years,
            "transition_years": transition_years,
            "stable_growth_rate": stable_growth_rate,
            "required_return": self.r,
            "intrinsic_value": intrinsic_value,
        }

    def margin_of_safety(self, intrinsic_value, current_price):
        """
        Calcula el margen de seguridad
        """
        if intrinsic_value is None or current_price is None:
            return None

        margin = ((intrinsic_value - current_price) / intrinsic_value) * 100

        return {
            "intrinsic_value": intrinsic_value,
            "current_price": current_price,
            "margin_of_safety_%": margin,
            "undervalued": margin > 0,
            "recommendation": self._get_recommendation(margin),
        }

    def _get_recommendation(self, margin):
        """
        Recomendación basada en margen de seguridad
        """
        if margin > 30:
            return "COMPRA FUERTE - Gran descuento"
        elif margin > 15:
            return "COMPRA - Buen descuento"
        elif margin > 0:
            return "COMPRA MODERADA - Ligero descuento"
        elif margin > -10:
            return "MANTENER - Precio justo"
        elif margin > -25:
            return "VENDER - Ligeramente sobrevalorada"
        else:
            return "VENDER FUERTE - Muy sobrevalorada"


# ================================================
# Función de ayuda para calcular tasa de crecimiento histórica
# ================================================
def calculate_historical_growth(dividends_list):
    """
    Calcula CAGR (Compound Annual Growth Rate) de dividendos históricos

    dividends_list: lista de dividendos anuales [más antiguo ... más reciente]
    """
    if len(dividends_list) < 2:
        return None

    start = dividends_list[0]
    end = dividends_list[-1]
    years = len(dividends_list) - 1

    if start <= 0 or end <= 0:
        return None

    cagr = (end / start) ** (1 / years) - 1

    return cagr


# ================================================
# Ejemplo de uso
# ================================================
if __name__ == "__main__":
    print("=" * 70)
    print("📊 EJEMPLO DE VALORACIÓN DDM - HASI")
    print("=" * 70)

    # Datos de ejemplo de HASI
    current_div_per_share = 1.63  # Del output anterior
    current_price = 33.42
    required_return = 0.10  # 10% retorno requerido

    # Crear modelo
    ddm = DividendDiscountModel(current_div_per_share, required_return)

    print("\n" + "-" * 70)
    print("1️⃣  GORDON GROWTH MODEL")
    print("-" * 70)

    # Escenario conservador: 3% crecimiento
    result = ddm.gordon_growth(growth_rate=0.03)
    print(f"\nCrecimiento constante: 3%")
    print(f"Valor Intrínseco: ${result['intrinsic_value']:.2f}")

    mos = ddm.margin_of_safety(result["intrinsic_value"], current_price)
    print(f"Margen de Seguridad: {mos['margin_of_safety_%']:.1f}%")
    print(f"Recomendación: {mos['recommendation']}")

    # Escenario optimista: 5% crecimiento
    result = ddm.gordon_growth(growth_rate=0.05)
    print(f"\nCrecimiento constante: 5%")
    print(f"Valor Intrínseco: ${result['intrinsic_value']:.2f}")

    mos = ddm.margin_of_safety(result["intrinsic_value"], current_price)
    print(f"Margen de Seguridad: {mos['margin_of_safety_%']:.1f}%")
    print(f"Recomendación: {mos['recommendation']}")

    print("\n" + "-" * 70)
    print("2️⃣  TWO-STAGE DDM")
    print("-" * 70)

    # 7% por 5 años, luego 3% perpetuo
    result = ddm.two_stage(high_growth_rate=0.07, high_growth_years=5, stable_growth_rate=0.03)

    print(f"\nAlto crecimiento: 7% por 5 años")
    print(f"Crecimiento estable: 3% perpetuo")
    print(f"Valor Intrínseco: ${result['intrinsic_value']:.2f}")

    mos = ddm.margin_of_safety(result["intrinsic_value"], current_price)
    print(f"Margen de Seguridad: {mos['margin_of_safety_%']:.1f}%")
    print(f"Recomendación: {mos['recommendation']}")

    print("\n" + "-" * 70)
    print("3️⃣  THREE-STAGE DDM")
    print("-" * 70)

    # 8% por 3 años, transición de 4 años, luego 3% perpetuo
    result = ddm.three_stage(
        high_growth_rate=0.08,
        high_growth_years=3,
        transition_years=4,
        stable_growth_rate=0.03,
    )

    print(f"\nAlto crecimiento: 8% por 3 años")
    print(f"Transición: 4 años")
    print(f"Crecimiento estable: 3% perpetuo")
    print(f"Valor Intrínseco: ${result['intrinsic_value']:.2f}")

    mos = ddm.margin_of_safety(result["intrinsic_value"], current_price)
    print(f"Margen de Seguridad: {mos['margin_of_safety_%']:.1f}%")
    print(f"Recomendación: {mos['recommendation']}")

    print("\n" + "=" * 70)
    print("✅ ANÁLISIS COMPLETADO")
    print("=" * 70)
