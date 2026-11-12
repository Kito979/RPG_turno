from __future__ import annotations
import math
import random as rd
from abc import ABC
from typing import List, Optional, Tuple, TYPE_CHECKING

from Creature import creature, creature_npc, opcao
from Classes import classe, cavaleiro, xama, sentinela
from Racas import raca, Besouro
from Equipamentos import Item, Arma, Espada, Arco
from Habilidades import skill
from Utils import ler_int, prob_acerto, rolar_sucessos

if TYPE_CHECKING:
    from Game import evento

CLASSES_DISPONIVEIS = [cavaleiro, xama, sentinela]
RACAS_DISPONIVEIS = [Besouro]

nomes = [
    "Vesper", "Gloom", "Cinder", "Marrow", "Shade", "Nettle", "Voss", "Thorn", "Rust", "Blight",
    "Chitin", "Mandible", "Thorax", "Elytra", "Stinger", "Carapace", "Palp", "Larva", "Pincer",
    "Silkweaver", "Kiris", "Ooma'ris", "Zanth", "Murn", "Phos", "Verid", "Skarn", "Velox",
    "Aethel", "Nox",
]


class humanoid(creature, ABC):
    Raca: raca
    lvl: int
    classeh: classe
    _seiva: int
    _quitina: int
    _ferroada: int
    _reflexo: int
    _alma: int
    inventariro: List[Item]
    arma_atual: int   # índice no inventário (-1 = sem arma)
    Norah: float

    def __init__(self, raca: raca, lvl, classeh: classe, seiva, quitina, ferroada, reflexo, alma, nome):
        self.Raca = raca
        self.lvl = 1
        self.classeh = classeh
        self._alma = alma         # ligado à magia
        self._reflexo = reflexo   # quão rápido você é
        self._quitina = quitina   # resistência da casca
        self._seiva = seiva       # regeneração/cura (reservado: ainda não há cura no jogo, não afeta a vitalidade)
        self._ferroada = ferroada # quão afiado é o ferrão (dano)
        self.Norah = 0
        self.inventariro = []
        self.arma_atual = -1
        super().__init__(nome, self.calcvt(), self.calcvg(), self.calcsnd())
        while self.lvl < lvl:
            self.lvl_up()

    # ------------------------------------------------------------ status
    def calcvt(self):
        return self.classeh.get_vt_base() + self.Raca.get_vt_base() + math.floor(self._reflexo)

    def calcvg(self):
        return self.classeh.get_vg_base() + self.Raca.get_vg_base() + math.floor(self._quitina / 2)

    def calcsnd(self):
        return self.classeh.get_snd_base() + self.Raca.get_snd_base() + math.floor(self._alma / 2)

    def get_ferroada(self):
        return self._ferroada

    def get_alma(self):
        return self._alma

    def calc_dt(self):
        return math.floor(self._reflexo / 2)

    def lvl_up(self):
        self.lvl += 1
        self.classeh.lvl_up(self)
        self.Raca.lvl_up(self)

    # ------------------------------------------------------------ skills e itens
    def todas_skills(self) -> List[skill]:
        return list(self.classeh.skills) + list(self.Raca.skills)

    def listaSkills(self):
        print('Skills de classe:')
        for sk in self.classeh.skills:
            print(f"  {sk}")
        print('Skills de raça:')
        for sk in self.Raca.skills:
            print(f"  {sk}")

    def arma_equipada(self) -> Optional[Arma]:
        if 0 <= self.arma_atual < len(self.inventariro):
            return self.inventariro[self.arma_atual]
        return None

    def adicionar_item(self, item: Item):
        self.inventariro.append(item)
        if self.arma_atual == -1 and item.get_tipo() == 1:
            self.arma_atual = len(self.inventariro) - 1

    def listar_itens(self):
        print("Itens no inventario:\n")
        for j, i in enumerate(self.inventariro, start=1):
            marca = " (equipada)" if j - 1 == self.arma_atual else ""
            print(f"{j} - {i.nome}{marca}\n")

    def trocar_arma(self):
        self.listar_itens()
        s = ler_int('Qual a arma que você vai equipar: ')
        if not 0 < s <= len(self.inventariro):
            raise Exception("Fora dos parametros")
        if self.inventariro[s - 1].get_tipo() != 1:
            raise Exception("Esse item não é uma arma principal")
        self.arma_atual = s - 1

    def meditar(self):
        r = 2
        n = rd.randint(1, 6)
        print(f"Rolagem 1: {n} | {'Passou' if n == 6 else 'Falhou'}")
        if n == 6:
            r += 1
        print(f"Recuperou {r} de vigor")
        self._vg = min(self._vgMax, self._vg + r)
        r = 1
        for i in range(2):
            n = rd.randint(1, 6)
            print(f"Rolagem {i + 1}: {n} | {'Passou' if n == 6 else 'Falhou'}")
            if n == 6:
                r += 1
        print(f"Recuperou {r} de sanidade")
        self._snd = min(self._sndMax, self._snd + r)

    # ------------------------------------------------------------ ataque desarmado
    def estimar_desarmado(self, alvo) -> Tuple[float, float]:
        return prob_acerto(1 + self._ferroada // 2, 3 + alvo.calc_dt()), 1.0

    def usar_desarmado(self, alvo):
        dt = 3 + alvo.calc_dt()
        rolagens = 1 + self._ferroada // 2
        if rolagens < dt:
            raise Exception("O alvo é forte demais (Impossivel acertar ou causar danos)")
        acertos = rolar_sucessos(rolagens)
        print(f"{acertos} sucessos (DT {dt})")
        if acertos >= dt:
            alvo.receber_dano(1)
            print(f"{self.nome} acertou {alvo.nome} e causou 1 de dano!")
        else:
            print("O ataque falhou")

    # ------------------------------------------------------------ posição inicial
    def definirPosicao(self, idx_grupo):
        """Arma equipada manda: corpo a corpo -> campo (0); ranged -> backline do grupo.
        Sem arma: a classe decide (cavaleiro/sentinela na frente, xamã atrás)."""
        arma = self.arma_equipada()
        if arma is not None:
            frente = arma.alcance == 1
        else:
            frente = self.classeh.fica_na_frente
        return 0 if frente else idx_grupo + 1

    def __str__(self):
        info = creature.__str__(self)
        info += f"Raça: {type(self.Raca).__name__} | Classe: {type(self.classeh).__name__} | Nível: {self.lvl}\n"
        info += (f"Seiva {self._seiva} | Quitina {self._quitina} | Ferroada {self._ferroada} | "
                 f"Reflexo {self._reflexo} | Alma {self._alma}\n")
        arma = self.arma_equipada()
        info += f"Arma: {arma.nome if arma else 'Desarmado'}\n"
        skills = self.todas_skills()
        info += "Skills: " + (", ".join(sk.nome for sk in skills) if skills else "nenhuma") + "\n"
        return info


class player(humanoid):
    jogador: str

    def __init__(self, jogador=None, nome=None, raca=None, classeh=None,
                 seiva=None, quitina=None, ferroada=None, reflexo=None, alma=None):
        """Sem argumentos: monta a ficha pelo terminal. Com argumentos (ex.: vindos de
        uma interface gráfica): cria direto, sem input()."""
        if nome is None:
            jogador, nome, raca, classeh, seiva, quitina, ferroada, reflexo, alma = self._ficha_terminal()
        self.jogador = jogador
        super().__init__(raca=raca, lvl=1, classeh=classeh, seiva=seiva, quitina=quitina,
                         ferroada=ferroada, reflexo=reflexo, alma=alma, nome=nome)

    @staticmethod
    def _ficha_terminal():
        jogador = input("Digite o nome do Player: ")
        nome = input("Digite o nome do personagem: ")
        print("12 pontos pra distribuir entre seiva, quitina, ferroada, reflexo e alma\nNenhum status pode ser menor 1 ou maior que 5")
        while True:
            try:
                pontos = 12
                seiva = ler_int("seiva: ")
                pontos -= seiva
                print(f"Pontos restantes: {pontos}")
                alma = ler_int("Alma: ")
                pontos -= alma
                print(f"Pontos restantes: {pontos}")
                quitina = ler_int("quitina: ")
                pontos -= quitina
                print(f"Pontos restantes: {pontos}")
                ferroada = ler_int("ferroada: ")
                pontos -= ferroada
                print(f"Pontos restantes: {pontos}")
                reflexo = ler_int("reflexo: ")
                pontos -= reflexo
                print(f"Pontos restantes: {pontos}")
                if pontos < 0:
                    raise Exception("Gastou mais pontos do que deveria")
                if pontos > 0:
                    raise Exception("Sobraram pontos para distribuir")
                if not all(1 <= x <= 5 for x in (seiva, alma, quitina, ferroada, reflexo)):
                    raise Exception("Algum dos estatus estão fora dos parametros")
                break
            except Exception as e:
                print(e)

        print("\nEscolha a Classe:")
        print("1 - Cavaleiro")
        print("2 - Xamã")
        print("3 - Sentinela")
        opcoes_classe = {1: cavaleiro, 2: xama, 3: sentinela}
        while True:
            try:
                op_classe = ler_int("Opção de classe: ")
                if op_classe not in opcoes_classe:
                    raise Exception("Opção inválida!")
                classe_escolhida = opcoes_classe[op_classe]()
                break
            except Exception as e:
                print(e)

        print("\nEscolha a Raça:")
        print("1 - Besouro")
        opcoes_raca = {1: Besouro}
        while True:
            try:
                op_raca = ler_int("Opção de raça: ")
                if op_raca not in opcoes_raca:
                    raise Exception("Opção inválida!")
                raca_escolhida = opcoes_raca[op_raca]()
                break
            except Exception as e:
                print(e)
        return jogador, nome, raca_escolhida, classe_escolhida, seiva, quitina, ferroada, reflexo, alma
    
        

    def usarSkill(self, game: 'evento', posicao):
        print("1 = Skills de classe\n2 = Skills de raça\n")
        s = ler_int('Qual grupo de skills: ')
        match s:
            case 1:
                lista = self.classeh.skills
            case 2:
                lista = self.Raca.skills
            case _:
                raise Exception("Fora dos parametros")
        if not lista:
            raise Exception("Nenhuma skill disponível nesse grupo")
        for j, sk in enumerate(lista, start=1):
            print(f'{j} = {sk}\n')
        s = ler_int('Qual skills vai usar: ')
        if not 0 < s <= len(lista):
            raise Exception("Fora dos parametros das skills")
        lista[s - 1].cogitar(game, posicao, self)

    def usar_item(self, game: 'evento', posicao):
        self.listar_itens()
        s = ler_int('Qual item que você vai usar: ')
        if not 0 < s <= len(self.inventariro):
            raise Exception("Fora dos parametros")
        item = self.inventariro[s - 1]
        if item.get_tipo() not in (2, 3, 4):
            raise Exception("Esse item é uma arma principal")
        item.verusar(game, self, posicao)
        if item.qntd <= 0:
            self.inventariro.pop(s - 1)
            if self.arma_atual > s - 1:
                self.arma_atual -= 1

    def atacar(self, game: 'evento', posicao):
        """Levanta Exception se não houver alvo ou se o ataque for cancelado."""
        arma = self.arma_equipada()
        if arma is None:
            self.verificar_acerto_desarmado(game, posicao)
        else:
            arma.verusar(game, self, posicao)

    def verificar_acerto_desarmado(self, game: 'evento', posicao):
        alvo = game.escolher_alvo(1, posicao)
        self.usar_desarmado(alvo)

    def acao(self, game: 'evento', posicao, idx):
        self.menu_de_acoes(game, posicao, idx)

    def menu_de_acoes(self, game: 'evento', posicao, idx):
        andou = False
        print(f"\nLista dos Grupos\n{game.mostrar_grupos()}\n")
        while True:
            print(f"\nNome: {self.nome}\nVitalidade: {self._vit}/{self._vitMax}\nVigor: {self._vg}/{self._vgMax}\n"
                  f"Mente {self._snd}/{self._sndMax}\nPosição: {game.nome_posicao(posicao)}\n"
                  "O que você fará nesse turno:\n1 - Atacar\n2 - Trocar arma principal\n3 - usar item\n"
                  "4 - Usar Habilidades\n5 - Avançar\n6 - Recuar\n7 - Meditar\n")
            s = ler_int("O que fará: ")
            try:
                match s:
                    case 1:
                        self.atacar(game, posicao)
                        break
                    case 2:
                        self.trocar_arma()
                        break
                    case 3:
                        self.usar_item(game, posicao)
                        break
                    case 4:
                        self.usarSkill(game, posicao)
                        break
                    case 5 | 6:
                        if andou:
                            raise Exception("Você já andou nesse turno")
                        nova = self.avancar(game, posicao) if s == 5 else self.recuar(game, posicao)
                        if nova == posicao:
                            raise Exception("Você não pode se mover nessa direção")
                        game.grupos[game.grupoAtual].mover(idx, nova)
                        posicao = nova   # ações seguintes usam a posição nova
                        andou = True
                        print(f"{self.nome} agora está em: {game.nome_posicao(nova)}")
                    case 7:
                        self.meditar()
                        break
                    case _:
                        raise Exception("Fora dos parametros")
            except Exception as e:
                print(e)

    def __str__(self):
        return f"Jogador: {self.jogador}\n" + humanoid.__str__(self)


class humanoidNPC(humanoid, creature_npc):
    """Humanoide controlado pela IA (usa arma, soco e skills)."""

    def __init__(self, raca, lvl, classe, seiva, quitina, ferroada, reflexo, alma, nome, arma: Optional[Item] = None):
        super().__init__(raca, lvl, classe, seiva, quitina, ferroada, reflexo, alma, nome)
        if arma is not None:
            self.adicionar_item(arma)

    @classmethod
    def aleatorio(cls, lvl=1, nome: Optional[str] = None):
        """Ficha instantânea: classe, raça, nome, atributos e arma sorteados."""
        classeh = rd.choice(CLASSES_DISPONIVEIS)()
        racah = rd.choice(RACAS_DISPONIVEIS)()
        a = {k: rd.randint(*v) for k, v in classeh.perfil.items()}
        arma = Arco() if not classeh.fica_na_frente else Espada()
        return cls(racah, lvl, classeh, a["seiva"], a["quitina"], a["ferroada"], a["reflexo"], a["alma"], nome or rd.choice(nomes), arma)

    # ------------------------------------------------------------ IA
    def alcance_ataque(self):
        arma = self.arma_equipada()
        return arma.alcance if arma is not None else 1

    def opcoes_de_ataque(self, game: 'evento', posicao) -> List[opcao]:
        ops: List[opcao] = []
        arma = self.arma_equipada()
        if arma is not None:
            ops += self.opcoes_alvos(game, posicao, arma.alcance, lambda a: arma.estimar(a, self), lambda a: arma.usar(a, self), "ataca {alvo} com " + arma.nome)
        # Soco: plano B de quem luta à distância (ou está desarmado). A nota favorece
        # o soco quando ele derruba um alvo quase morto.
        ops += self.opcoes_alvos(game, posicao, 1, self.estimar_desarmado,
                                 self.usar_desarmado, "bate desarmado em {alvo}")
        for sk in self.todas_skills():
            if sk.alcance in (1, 2) and sk.utilizavel(self):
                ops += self.opcoes_alvos(game, posicao, sk.alcance,
                                         lambda a, sk=sk: sk.estimar(self, a),
                                         lambda a, sk=sk: sk.usar(a, self),
                                         "usa " + sk.nome + " em {alvo}", bonus=1.1)
        return ops

    def opcoes_utilitarias(self, game: 'evento', posicao, melhor_ataque) -> List[opcao]:
        ops: List[opcao] = []
        for sk in self.todas_skills():
            if sk.alcance == 0 and sk.utilizavel(self) and self._vittemp == 0:
                ferido = 1 - self._vit / self._vitMax
                ops.append(opcao(max(melhor_ataque, 0.5) * (0.4 + ferido), "usa " + sk.nome,
                                 lambda sk=sk: sk.usar(self, self)))
        falta = (1 - self._vg / self._vgMax) + (1 - self._snd / self._sndMax)
        if falta >= 0.5:
            ops.append(opcao(0.2 + 0.3 * falta, "medita", self.meditar))
        return ops

    def __str__(self):
        return humanoid.__str__(self) + self.str_afiliacoes()
