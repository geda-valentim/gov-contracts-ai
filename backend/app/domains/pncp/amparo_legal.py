"""
PNCP Domain: Amparo Legal.

Defines the legal basis for procurement processes according to Lei 14.133/2021.
"""

from enum import Enum


class AmparoLegal(int, Enum):
    """
    Amparo legal da contratação (Lei 14.133/2021 e outras).

    Reference: PNCP API Documentation - Section 5.15
    """

    # Lei 14.133/2021, Art. 28 (Licitação)
    LEI_14133_ART_28_I = 1
    LEI_14133_ART_28_II = 2
    LEI_14133_ART_28_III = 3
    LEI_14133_ART_28_IV = 4
    LEI_14133_ART_28_V = 5

    # Lei 14.133/2021, Art. 74 (Dispensa)
    LEI_14133_ART_74_I = 6
    LEI_14133_ART_74_II = 7
    LEI_14133_ART_74_III_A = 8
    LEI_14133_ART_74_III_B = 9
    LEI_14133_ART_74_III_C = 10
    LEI_14133_ART_74_III_D = 11
    LEI_14133_ART_74_III_E = 12
    LEI_14133_ART_74_III_F = 13
    LEI_14133_ART_74_III_G = 14
    LEI_14133_ART_74_III_H = 15
    LEI_14133_ART_74_IV = 16
    LEI_14133_ART_74_V = 17
    LEI_14133_ART_74_CAPUT = 50

    # Lei 14.133/2021, Art. 75 (Dispensa)
    LEI_14133_ART_75_I = 18
    LEI_14133_ART_75_II = 19
    LEI_14133_ART_75_III_A = 20
    LEI_14133_ART_75_III_B = 21
    LEI_14133_ART_75_IV_A = 22
    LEI_14133_ART_75_IV_B = 23
    LEI_14133_ART_75_IV_C = 24
    LEI_14133_ART_75_IV_D = 25
    LEI_14133_ART_75_IV_E = 26
    LEI_14133_ART_75_IV_F = 27
    LEI_14133_ART_75_IV_G = 28
    LEI_14133_ART_75_IV_H = 29
    LEI_14133_ART_75_IV_I = 30
    LEI_14133_ART_75_IV_J = 31
    LEI_14133_ART_75_IV_K = 32
    LEI_14133_ART_75_IV_L = 33
    LEI_14133_ART_75_IV_M = 34
    LEI_14133_ART_75_V = 35
    LEI_14133_ART_75_VI = 36
    LEI_14133_ART_75_VII = 37
    LEI_14133_ART_75_VIII = 38
    LEI_14133_ART_75_IX = 39
    LEI_14133_ART_75_X = 40
    LEI_14133_ART_75_XI = 41
    LEI_14133_ART_75_XII = 42
    LEI_14133_ART_75_XIII = 43
    LEI_14133_ART_75_XIV = 44
    LEI_14133_ART_75_XV = 45
    LEI_14133_ART_75_XVI = 46
    LEI_14133_ART_75_XVII = 60
    LEI_14133_ART_75_XVIII = 77

    # Lei 14.133/2021, Art. 76 (Inexigibilidade)
    LEI_14133_ART_76_I_A = 61
    LEI_14133_ART_76_I_B = 62
    LEI_14133_ART_76_I_C = 63
    LEI_14133_ART_76_I_D = 64
    LEI_14133_ART_76_I_E = 65
    LEI_14133_ART_76_I_F = 66
    LEI_14133_ART_76_I_G = 67
    LEI_14133_ART_76_I_H = 68
    LEI_14133_ART_76_I_I = 69
    LEI_14133_ART_76_I_J = 70
    LEI_14133_ART_76_II_A = 71
    LEI_14133_ART_76_II_B = 72
    LEI_14133_ART_76_II_C = 73
    LEI_14133_ART_76_II_D = 74
    LEI_14133_ART_76_II_E = 75
    LEI_14133_ART_76_II_F = 76

    # Lei 14.133/2021, Art. 78 (Emergência)
    LEI_14133_ART_78_I = 47
    LEI_14133_ART_78_II = 48
    LEI_14133_ART_78_III = 49

    # Lei 14.133/2021 - Outros
    LEI_14133_ART_1_PARAGRAFO_2 = 80

    # Lei 14.284/2021 (SPU)
    LEI_14284_ART_29_CAPUT = 51
    LEI_14284_ART_24_PARAGRAFO_1 = 52
    LEI_14284_ART_25_PARAGRAFO_1 = 53
    LEI_14284_ART_34 = 54

    # Lei 9.636/1998 (SPU)
    LEI_9636_ART_11C_I = 55
    LEI_9636_ART_11C_II = 56
    LEI_9636_ART_24C_I = 57
    LEI_9636_ART_24C_II = 58
    LEI_9636_ART_24C_III = 59

    # Lei 14.628/2023 (Mercado Regulado de Carbono)
    LEI_14628_ART_4 = 78
    LEI_14628_ART_12 = 79

    @property
    def descricao(self) -> str:
        """Retorna descrição do amparo legal."""
        return self.name.replace("_", " ")

    @property
    def artigo(self) -> str:
        """Retorna número do artigo formatado."""
        parts = self.name.split("_ART_")
        if len(parts) == 2:
            lei = parts[0].replace("_", " ")
            artigo = parts[1].replace("_", ", ")
            return f"{lei}, Art. {artigo}"
        return self.name

    @property
    def is_dispensavel(self) -> bool:
        """Verifica se é dispensa de licitação."""
        return "ART_74" in self.name or "ART_75" in self.name or "ART_78" in self.name

    @property
    def is_inexigivel(self) -> bool:
        """Verifica se é inexigibilidade."""
        return "ART_76" in self.name

    @property
    def is_licitacao_obrigatoria(self) -> bool:
        """Verifica se requer licitação obrigatória."""
        return "ART_28" in self.name

    @property
    def is_emergency(self) -> bool:
        """Verifica se é contratação emergencial."""
        return "ART_78" in self.name
