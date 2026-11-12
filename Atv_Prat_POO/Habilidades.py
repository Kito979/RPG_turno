from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Tuple, TYPE_CHECKING

from Utils import prob_acerto, rolar_sucessos, rolar_explosivo, bonus_esperado_explosivo

if TYPE_CHECKING:
    from Humanoid import humanoid
    from Creature import creature
    from Game import evento


class skill(ABC):
    nome: str
    alcance: int   # 0 = uso pessoal | 1 = corpo a corpo | 2 = ranged
    DTbase: int
    custo_vg: int
    custo_snd: int
    descricao: str

    def __init__(self, nome, alcance, DTbase=0, custo_vg=0, custo_snd=0, descricao=""):
        self.nome = nome
        self.alcance = alcance
        self.DTbase = DTbase
        self.custo_vg = custo_vg
        self.custo_snd = custo_snd
        self.descricao = descricao

    # ---------------------------------------------------------- requisitos
    def recursos_ok(self, h: 'humanoid'):
        """Levanta Exception se faltar vigor ou sanidade."""
        if h.get_vg() < self.custo_vg:
            raise Exception("Vigor insuficiente!")
        if h.get_snd() < self.custo_snd:
            raise Exception("Sanidade insuficiente!")

    def arma_compativel(self, h: 'humanoid') -> bool:
        return True

    def utilizavel(self, h: 'humanoid') -> bool:
        """Versão silenciosa dos requisitos (usada pela IA)."""
        try:
            self.recursos_ok(h)
        except Exception:
            return False
        return self.arma_compativel(h)

    def pagar(self, h: 'humanoid'):
        h._vg -= self.custo_vg
        h._snd -= self.custo_snd

    # ---------------------------------------------------------- execução
    @abstractmethod
    def cogitar(self, game: 'evento', posicao, h: 'humanoid'):
        """Levanta Exception se a skill não puder/foi cancelada (assim ela não gasta a ação)."""
        pass

    @abstractmethod
    def usar(self, alvo: 'creature', h: 'humanoid'):
        pass

    def estimar(self, h: 'humanoid', alvo: 'creature') -> Tuple[float, float]:
        """(chance de acerto, dano esperado) - usado pela IA."""
        return 0.0, 0.0

    def __str__(self):
        alc = {0: "uso pessoal", 1: "corpo a corpo", 2: "à distância"}.get(self.alcance, "?")
        info = f"{self.nome} | Alcance: {alc} | DT {self.DTbase} | Custo: {self.custo_vg} vigor, {self.custo_snd} sanidade"
        if self.descricao:
            info += f"\n    {self.descricao}"
        return info



class skillAtaque(skill, ABC):
    """Skill ofensiva: rola para acertar (DT) e depois rola dados explosivos de dano."""

    @abstractmethod
    def rolagens_acerto(self, h: 'humanoid') -> int:
        pass

    @abstractmethod
    def dano_base(self, h: 'humanoid') -> int:
        pass

    def dados_dano(self, h: 'humanoid') -> int:
        return 1 + h.get_ferroada() // 2

    def estimar(self, h, alvo):
        dt = self.DTbase + alvo.calc_dt()
        prob = prob_acerto(self.rolagens_acerto(h), dt)
        return prob, self.dano_base(h) + bonus_esperado_explosivo(self.dados_dano(h))

    def cogitar(self, game, posicao, h):
        self.recursos_ok(h)
        if not self.arma_compativel(h):
            raise Exception("Arma inválida para a skill")
        alvo = game.escolher_alvo(self.alcance, posicao)   # levanta Exception se cancelar/sem alvo
        self.usar(alvo, h)

    def usar(self, alvo, h):
        dt = self.DTbase + alvo.calc_dt()
        rolagens = self.rolagens_acerto(h)
        if rolagens < dt:
            raise Exception("O alvo é forte demais (Impossivel acertar)")
        self.pagar(h)
        acertos = rolar_sucessos(rolagens)
        print(f"{acertos} sucessos (DT {dt})")
        if acertos < dt:
            print("O ataque falhou")
            return
        bonus, historico = rolar_explosivo(self.dados_dano(h))
        print(f"Dados de dano (5 ou 6 soma +1 e rola outro): {historico}")
        dano = self.dano_base(h) + bonus
        alvo.receber_dano(dano)
        print(f"{h.nome} acertou {alvo.nome} e causou {dano} de dano!")


class skill_golpe_de_foco_absoluto(skillAtaque):
    def __init__(self):
        super().__init__(nome="Golpe de foco absoluto", alcance=1, DTbase=1, custo_vg=2, custo_snd=1,
                         descricao="Golpe corpo a corpo com dados de dano explosivos.")

    def arma_compativel(self, h):
        arma = h.arma_equipada()
        return arma is None or arma.alcance == 1

    def rolagens_acerto(self, h):
        return 2 + h.get_ferroada() // 2

    def dano_base(self, h):
        arma = h.arma_equipada()
        return 2 if arma is None else arma.danoBase


class skill_disparo_de_foco_absoluto(skillAtaque):
    def __init__(self):
        super().__init__(nome="Disparo de foco absoluto", alcance=2, DTbase=2, custo_vg=1, custo_snd=2,
                         descricao="Disparo de energia à distância, guiado pela Alma.")

    def rolagens_acerto(self, h):
        return self.DTbase + h.get_alma() // 2

    def dano_base(self, h):
        return 1


class skill_vit_arruinada(skill):
    def __init__(self):
        super().__init__(nome="Vitalidade arruinada", alcance=0, DTbase=0, custo_vg=1, custo_snd=3,
                         descricao="Concede a si mesmo vida temporária igual a Alma + 2.")

    def cogitar(self, game, posicao, h):
        self.recursos_ok(h)
        self.usar(h, h)

    def usar(self, alvo, h):
        self.pagar(h)
        valor = h.get_alma() + 2
        alvo.adicionarvttemp(valor)
        print(f"{h.nome} usou Vitalidade Arruinada e concedeu a si {valor} de vida temporária!")
