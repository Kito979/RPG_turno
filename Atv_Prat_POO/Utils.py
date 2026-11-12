import math
import random as rd


def ler_int(msg=""):
    """input() que não quebra o jogo se o usuário digitar texto."""
    while True:
        try:
            return int(input(msg))
        except ValueError:
            print("Digite um número inteiro.")


def ler_sim_nao(msg=""):
    """Pergunta de sim/não. Retorna True para sim e False para não."""
    while True:
        try:
            r = input(f"{msg} (s/n): ").strip().lower()
            if r in ("s", "sim", "si", "y"):
                return True
            if r in ("n", "nao", "não", "no", "ñ"):
                return False
            raise Exception("Responda com s ou n.")
        except Exception as e:
            print(e)


# ---------------------------------------------------------------- dados
# Um dado é "sucesso" quando sai 5 ou 6 (chance de 1/3).
CHANCE_SUCESSO = 1 / 3


def rolar_sucessos(qtd):
    """Rola 'qtd' d6 e conta quantos deram 5 ou 6."""
    return sum(1 for _ in range(qtd) if rd.randint(1, 6) >= 5)


def rolar_explosivo(base):
    """Rola 'base' d6. Cada 5/6 soma +1 e concede +1d6 extra; cada dado que
    falha é consumido. Retorna (bonus, historico_das_rolagens)."""
    restantes = base
    bonus = 0
    historico = []
    while restantes > 0:
        r = rd.randint(1, 6)
        historico.append(r)
        if r >= 5:
            bonus += 1
        else:
            restantes -= 1
    return bonus, historico


def bonus_esperado_explosivo(base):
    """Valor esperado do bônus de rolar_explosivo(base)."""
    p = CHANCE_SUCESSO
    return base * p / (1 - p)


def prob_acerto(rolagens, dt):
    """Probabilidade de conseguir pelo menos 'dt' sucessos em 'rolagens' d6.
    DT <= 0 é acerto garantido; DT > rolagens é impossível."""
    if dt <= 0:
        return 1.0
    if rolagens < dt:
        return 0.0
    p = CHANCE_SUCESSO
    return sum(math.comb(rolagens, k) * p ** k * (1 - p) ** (rolagens - k)
               for k in range(dt, rolagens + 1))
