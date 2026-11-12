from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Tuple, TYPE_CHECKING

from Utils import prob_acerto, rolar_sucessos

if TYPE_CHECKING:
    from Humanoid import humanoid
    from Creature import creature
    from Game import evento


class Upgrade(ABC):
    nome: str
    _usoslot: int

    def __init__(self, slotuso):
        self._usoslot = slotuso

    def get_usoslot(self):
        return self._usoslot

    @abstractmethod
    def equipar(self, equipamento: 'Item'):
        pass

    def __str__(self):
        return f'Consumo de slots: {self._usoslot}\n'


class Item(ABC):
    nome: str
    _tipo: int      # 1 = Arma Principal || 2 = Relíquias || 3 = Gadget || 4 Itens de utilidade
    alcance: int    # 0 = Uso pessoal || 1 = corpo a corpo || 2 = Ranged
    danoBase: int   # Aqui também é cura
    qntd: int       # quantidade
    preco: float    # Valor de venda ou compra
    DTbase: int     # sucessos mínimos para acerto || 0 = garantido
    slotDisp: int   # quantidade de upgrades disponíveis
    upgrades: List[Upgrade]

    def __init__(self, nome, tipo, alcance, Dano, qntd=1, preco=0, DT=0, slotDisp=0):
        self.nome = nome
        self._tipo = tipo
        self.alcance = alcance
        self.danoBase = Dano
        self.qntd = qntd
        self.preco = preco
        self.DTbase = DT
        self.slotDisp = slotDisp
        self.upgrades = []

    def get_tipo(self):
        return self._tipo

    @abstractmethod
    def verusar(self, game: 'evento', h: 'humanoid', posicao):
        """Levanta Exception se o item não pôde ser usado ou foi cancelado."""
        pass

    def melhorar(self, upgrade: Upgrade):
        if upgrade.get_usoslot() > self.slotDisp:
            raise Exception("Slots insuficientes para esse upgrade")
        self.upgrades.append(upgrade)
        self.slotDisp -= upgrade.get_usoslot()
        upgrade.equipar(self)

    def __str__(self):
        resp = f'Nome do item: {self.nome}\n'
        match self._tipo:
            case 1:
                resp += 'Tipo: Arma Principal\n'
            case 2:
                resp += 'Tipo: Relíquia\n'
            case 3:
                resp += 'Tipo: Gadget\n'
            case 4:
                resp += 'Tipo: Item de utilidade\n'
        resp += f'Dano base: {self.danoBase}\n'
        resp += f'DT base: {self.DTbase}\n'
        match self.alcance:
            case 1:
                resp += 'Alcance: corpo a corpo\n'
            case 2:
                resp += 'Alcance: à distância (não acerta quem está na mesma posição)\n'
            case _:
                resp += 'Para uso pessoal\n'
        if self.slotDisp > 0:
            resp += f'Slots disponíveis para Upgrade: {self.slotDisp}\n'
        else:
            resp += 'Sem slots para upgrade\n'
        if self.upgrades:
            resp += 'Upgrades equipados:\n'
            for i in self.upgrades:
                resp += str(i)
        return resp


class Arma(Item, ABC):
    """Arma principal (tipo 1). Espada e Arco só mudam alcance e valores."""

    def rolagens_de(self, h: 'humanoid') -> int:
        return 2 + h.get_ferroada() // 2

    def estimar(self, alvo: 'creature', h: 'humanoid') -> Tuple[float, float]:
        """(chance de acerto, dano) - usado pela IA."""
        return prob_acerto(self.rolagens_de(h), self.DTbase + alvo.calc_dt()), float(self.danoBase)

    def verusar(self, game, h, posicao):
        alvo = game.escolher_alvo(self.alcance, posicao)   # levanta Exception se cancelar/sem alvo
        self.usar(alvo, h)

    def usar(self, c: 'creature', h: 'humanoid'):
        dt = self.DTbase + c.calc_dt()
        rolagens = self.rolagens_de(h)
        if rolagens < dt:
            raise Exception("O alvo é forte demais (Impossivel acertar)")
        acertos = rolar_sucessos(rolagens)
        print(f"{acertos} sucessos (DT {dt})")
        if acertos >= dt:
            c.receber_dano(self.danoBase)
            print(f"{h.nome} acertou {c.nome} e causou {self.danoBase} de dano!")
        else:
            print("O ataque falhou")


class Espada(Arma):
    def __init__(self, nome="Espada lascada", tipo=1, alcance=1, dano=1, qntd=1, preco=0, dt=1, slot=1):
        super().__init__(nome, tipo, alcance, dano, qntd, preco, dt, slot)


class Arco(Arma):
    def __init__(self, nome="Arco frouxo", tipo=1, alcance=2, dano=1, qntd=1, preco=0, dt=1, slot=1):
        super().__init__(nome, tipo, alcance, dano, qntd, preco, dt, slot)
