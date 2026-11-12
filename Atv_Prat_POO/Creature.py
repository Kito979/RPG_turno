from __future__ import annotations
import random as rd
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, List, Tuple, TYPE_CHECKING

from Utils import ler_int, prob_acerto, rolar_sucessos

if TYPE_CHECKING:
    from Humanoid import humanoid
    from Habilidades import skill
    from Game import evento

# Posições (numeração global, igual para todos os grupos):
#   0     = campo de batalha
#   g + 1 = backline do grupo de índice g   (g0 -> 1, g1 -> 2, ...)

FATOR_MOVER = 0.85   # penalidade de um plano que exige se mover antes de agir
CHANCE_CAOS = 0.10   # chance do NPC ignorar a lógica e escolher qualquer opção viável


@dataclass
class opcao:
    """Uma jogada que a IA pode fazer: pontuação, descrição e a função que executa."""
    score: float
    texto: str
    executar: Callable[[], None]


class creature(ABC):
    nome : str
    _vit : int     #vt = vitalidade/vida se zerar morre/cai
    _vitMax : int
    _vittemp : int #vit temporaria
    _vg: int
    _vgMax: int
    _snd: int
    _sndMax : int

    def __init__(self, nome : str, vit : int, vg : int, snd : int):
        self.nome = nome
        self._vit = vit
        self._vitMax = vit
        self._vittemp = 0
        self._vg = vg
        self._vgMax = vg
        self._snd = snd
        self._sndMax = snd

    @abstractmethod
    def atacar(self, game : 'evento', posicao):
        pass

    @abstractmethod
    def acao(self, game : 'evento', posicao, idx):
        pass

    def definirPosicao(self, idx_grupo):
        """Posição inicial no combate. Padrão: backline do próprio grupo."""
        return idx_grupo + 1

    def adicionarvttemp(self, vittemp):
        self._vittemp += vittemp

    def calc_dt(self):
        return 0

    def get_vida(self):
        return self._vit

    def get_vida_max(self):
        return self._vitMax

    def get_vida_temp(self):
        return self._vittemp

    def get_snd(self):
        return self._snd

    def get_vg(self):
        return self._vg

    def esta_vivo(self):
        return self._vit > 0

    def restaurar(self):
        self._vit = self._vitMax
        self._vittemp = 0
        self._vg = self._vgMax
        self._snd = self._sndMax

    def receber_dano(self, dano):
        if dano <= 0:
            return
        if self._vittemp > 0:          # vida temporária absorve primeiro
            absorvido = min(self._vittemp, dano)
            self._vittemp -= absorvido
            dano -= absorvido
        self._vit = max(0, self._vit - dano)

    # ------------------------------------------------------------ movimento
    def destinos_avanco(self, game : 'evento', posicao) -> List[int]:
        """Posições para onde é possível avançar (sem input).
        backline própria -> campo | campo -> backline de cada grupo inimigo vivo"""
        if posicao == 0:
            return [i + 1 for i, g in enumerate(game.grupos)
                    if i != game.grupoAtual and g.verificar_grupo_vivo()]
        if posicao == game.grupoAtual + 1:
            return [0]
        return []   # já está na backline inimiga

    def destino_recuo(self, game : 'evento', posicao) -> int:
        """campo -> backline própria | backline inimiga -> campo"""
        if posicao == 0:
            return game.grupoAtual + 1
        if posicao != game.grupoAtual + 1 and posicao > 0:
            return 0
        return posicao

    def destinos_possiveis(self, game : 'evento', posicao) -> List[int]:
        """Posição atual + tudo que dá pra alcançar com um movimento."""
        ds = [posicao]
        for d in self.destinos_avanco(game, posicao) + [self.destino_recuo(game, posicao)]:
            if d not in ds:
                ds.append(d)
        return ds

    def avancar(self, game : 'evento', posicao):
        """Retorna a nova posição (ou a mesma se não puder avançar)."""
        destinos = self.destinos_avanco(game, posicao)
        if not destinos:
            return posicao
        if len(destinos) == 1:
            return destinos[0]
        for d in destinos:
            print(f"{d} - {game.nome_posicao(d)}")
        while True:
            try:
                s = ler_int("Avançar até qual posição: ")
                if s not in destinos:
                    raise Exception("Posição inválida")
                return s
            except Exception as e:
                print(e)

    def recuar(self, game : 'evento', posicao):
        return self.destino_recuo(game, posicao)

    def __str__(self):
        vida = f'{self._vit}/{self._vitMax}'
        if self._vittemp > 0:
            vida += f' (+{self._vittemp} temporária)'
        info = f'Nome: {self.nome}\n'
        info += f'Vida: {vida}\n'
        info += f'Vigor: {self._vg}/{self._vgMax}\n'
        info += f'Sanidade: {self._snd}/{self._sndMax}\n'
        return info


class creature_npc(creature):
    """Criatura controlada pela IA.

    A IA monta "planos" (se mover ou não + uma ação), dá uma nota a cada um
    (chance de acerto x dano esperado, bônus se derrubar o alvo, bônus por alvo
    ferido, penalidade por mover e por ficar exposto ao corpo a corpo) e sorteia
    um deles com peso proporcional à nota². Resultado: jogadas aleatórias, mas
    que tendem às melhores."""
    afiliacao : List['humanoid']
    skills : List['skill']
    tipo : int #1 = corpo a corpo 2 = range
    dano : int
    rolagens : int
    dt_ataque : int
    defesa : int

    def __init__(self, nome, vit, vg, snd, tipo=1, dano=1, rolagens=2, dt=1, defesa=0):
        super().__init__(nome, vit, vg, snd)
        self.tipo = tipo
        self.dano = dano
        self.rolagens = rolagens
        self.dt_ataque = dt
        self.defesa = defesa      # DT extra que os inimigos precisam vencer
        self.afiliacao = []
        self.skills = []

    def calc_dt(self):
        return self.defesa

    def alcance_ataque(self):
        return self.tipo

    # ------------------------------------------------------------ posição
    def definirPosicao(self, idx_grupo):
        """Corpo a corpo vai pro campo; ranged fica na backline."""
        return 0 if self.alcance_ataque() == 1 else idx_grupo + 1

    # ------------------------------------------------------------ ataque básico
    def estimar_ataque(self, alvo) -> Tuple[float, float]:
        return prob_acerto(self.rolagens, self.dt_ataque + alvo.calc_dt()), float(self.dano)

    def usar_ataque(self, alvo):
        dt = self.dt_ataque + alvo.calc_dt()
        if self.rolagens < dt:
            raise Exception("O alvo é forte demais (Impossivel acertar)")
        acertos = rolar_sucessos(self.rolagens)
        print(f"{acertos} sucessos (DT {dt})")
        if acertos >= dt:
            alvo.receber_dano(self.dano)
            print(f"{self.nome} acertou {alvo.nome} e causou {self.dano} de dano!")
        else:
            print("O ataque falhou")

    # ------------------------------------------------------------ ataque desarmado
    def estimar_desarmado(self, alvo) -> Tuple[float, float]:
        """Chance e dano de um soco (corpo a corpo, 1 de dano, DT 1)."""
        return prob_acerto(self.rolagens, 1 + alvo.calc_dt()), 1.0

    def usar_desarmado(self, alvo):
        dt = 1 + alvo.calc_dt()
        if self.rolagens < dt:
            raise Exception("O alvo é forte demais (Impossivel acertar)")
        acertos = rolar_sucessos(self.rolagens)
        print(f"{acertos} sucessos (DT {dt})")
        if acertos >= dt:
            alvo.receber_dano(1)
            print(f"{self.nome} acertou {alvo.nome} e causou 1 de dano!")
        else:
            print("O ataque falhou")

    # ------------------------------------------------------------ IA
    def valor_do_alvo(self, alvo, prob, dano) -> float:
        """Nota de atacar 'alvo' com chance 'prob' e dano 'dano'."""
        if prob <= 0 or dano <= 0:
            return 0.0
        valor = prob * dano
        if dano >= alvo.get_vida() + alvo.get_vida_temp():
            valor *= 2.0                                   # pode derrubar: prioridade
        ferido = 1 - alvo.get_vida() / alvo.get_vida_max()
        return valor * (1 + 0.5 * ferido)                  # prefere alvos feridos

    def opcoes_alvos(self, game : 'evento', posicao, alcance, estimar, usar, rotulo, bonus=1.0) -> List[opcao]:
        """Uma opção para cada alvo válido. 'rotulo' pode ter {alvo}."""
        ops = []
        for alvo in game.alvos_validos(alcance, posicao):
            prob, dano = estimar(alvo)
            v = self.valor_do_alvo(alvo, prob, dano) * bonus
            if v > 0:
                ops.append(opcao(v, rotulo.format(alvo=alvo.nome), lambda a=alvo: usar(a)))
        return ops

    def opcoes_de_ataque(self, game : 'evento', posicao) -> List[opcao]:
        """Ataques possíveis ESTANDO em 'posicao' (pode ser uma posição hipotética)."""
        ops = self.opcoes_alvos(game, posicao, self.alcance_ataque(),self.estimar_ataque, self.usar_ataque, "ataca {alvo}")
        if self.alcance_ataque() == 2:
            # Ranged não acerta quem está na mesma posição, mas pode socar.
            # A nota já favorece o soco quando ele derruba um alvo quase morto.
            ops += self.opcoes_alvos(game, posicao, 1, self.estimar_desarmado, self.usar_desarmado, "bate desarmado em {alvo}")
        return ops

    def opcoes_utilitarias(self, game : 'evento', posicao, melhor_ataque) -> List[opcao]:
        """Jogadas que não dependem de alvo/posição (curar, meditar...)."""
        return []

    def fator_exposicao(self, game : 'evento', posicao) -> float:
        """Quanto mais inimigos na mesma posição (podem me acertar no corpo a corpo),
        menor a nota. Pesa mais se estou ferido ou se luto à distância."""
        expostos = len(game.alvos_validos(1, posicao))
        if expostos == 0:
            return 1.0
        ferido = 1 - self._vit / self._vitMax
        peso = 0.08 + 0.25 * ferido + (0.10 if self.alcance_ataque() == 2 else 0.0)
        return 1 / (1 + peso * expostos)

    def planejar(self, game : 'evento', posicao) -> List[Tuple[float, int, opcao]]:
        """Lista de (nota, posição_onde_agir, opcao)."""
        planos = []
        for d in self.destinos_possiveis(game, posicao):
            fator = (1.0 if d == posicao else FATOR_MOVER) * self.fator_exposicao(game, d)
            for op in self.opcoes_de_ataque(game, d):
                planos.append((op.score * fator, d, op))
        melhor = max((p[0] for p in planos), default=0.0)
        for op in self.opcoes_utilitarias(game, posicao, melhor):
            if op.score > 0:
                planos.append((op.score * self.fator_exposicao(game, posicao), posicao, op))
        return planos

    def escolher_plano(self, planos):
        if not planos:
            return None
        if rd.random() < CHANCE_CAOS:
            return rd.choice(planos)
        pesos = [max(p[0], 0.01) ** 2 for p in planos]
        return rd.choices(planos, weights=pesos, k=1)[0]

    def mover(self, game : 'evento', idx, nova):
        g = game.grupos[game.grupoAtual]
        antiga = g.posicao[idx]
        g.mover(idx, nova)
        print(f"{self.nome} se move: {game.nome_posicao(antiga)} -> {game.nome_posicao(nova)}")

    def aproximar(self, game : 'evento', posicao, idx):
        """Ninguém ao alcance nem movendo: caminha em direção aos inimigos."""
        destinos = self.destinos_avanco(game, posicao)
        if not destinos:
            print(f"{self.nome} aguarda.")
            return
        melhor = max(len(game.alvos_validos(1, d)) for d in destinos)
        self.mover(game, idx, rd.choice([d for d in destinos if len(game.alvos_validos(1, d)) == melhor]))

    def acao(self, game : 'evento', posicao, idx):
        escolhido = self.escolher_plano(self.planejar(game, posicao))
        if escolhido is None:
            self.aproximar(game, posicao, idx)
            return
        _, destino, op = escolhido
        try:
            if destino != posicao:
                self.mover(game, idx, destino)
            print(f"{self.nome} {op.texto}")
            op.executar()
        except Exception as e:
            print(f"{self.nome} falhou: {e}")

    def atacar(self, game : 'evento', posicao):
        """Ataca sem se mover. Retorna True se atacou."""
        ops = self.opcoes_de_ataque(game, posicao)
        if not ops:
            return False
        op = rd.choices(ops, weights=[o.score ** 2 for o in ops], k=1)[0]
        print(f"{self.nome} {op.texto}")
        try:
            op.executar()
        except Exception as e:
            print(f"{self.nome} falhou: {e}")
            return False
        return True

    # ------------------------------------------------------------ gestão
    def afiliar(self, h : 'humanoid'):
        self.afiliacao.append(h)

    def desafiliar(self):
        print("Afiliados a esse NPC:\n")
        j = 0
        for i in self.afiliacao:
            j += 1
            print(f"{j} = {i.nome}\n")
        try:
            s = ler_int("Quem esse NPC desafiliou: ")
            if not 0 < s <= len(self.afiliacao):
                raise Exception("Afiliado inválido")
            self.afiliacao.pop(s-1)
        except Exception as e:
            print(e)

    def adicinionar_skills(self, s:'skill'):
        self.skills.append(s)

    def remover_skill(self):
        print("Skills desse NPC:\n")
        j = 0
        for i in self.skills:
            j += 1
            print(f"{j} = {i.nome}\n")
        try:
            s = ler_int("Qual skill será removida desse NPC: ")
            if not 0 < s <= len(self.skills):
                raise Exception("Skill inválida")
            self.skills.pop(s-1)
        except Exception as e:
            print(e)

    def str_afiliacoes(self):
        info = "\nLista das afiliações\n"
        for j, i in enumerate(self.afiliacao, start=1):
            info += f'Afiliação {j}: {i.nome}\n'
        return info

    def __str__(self):
        info = creature.__str__(self)
        info += f"Tipo: {'Corpo a corpo' if self.tipo == 1 else 'À distância'}\n"
        info += (f"Ataque: {self.dano} de dano | {self.rolagens} dados | "
                 f"DT {self.dt_ataque} | Defesa: {self.defesa}\n")
        info += "\nLista das skills\n"
        for j, i in enumerate(self.skills, start=1):
            info += f'skill {j}: {i}\n'
        return info + self.str_afiliacoes()
