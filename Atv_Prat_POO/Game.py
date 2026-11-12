from __future__ import annotations
from abc import ABC
from typing import List, Optional, Tuple

from Creature import creature, creature_npc
from Utils import ler_int

# ---------------------------------------------------------------- posições
#   0     = campo de batalha
#   g + 1 = backline do grupo de índice g   (g0 -> 1, g1 -> 2, ...)
#
# Alcance:  1 = corpo a corpo -> só acerta quem está NA MESMA posição que o atacante
#           2 = ranged        -> acerta qualquer posição, EXCETO a mesma do atacante


def pode_atingir(alcance: int, origem: int, destino: int) -> bool:
    if alcance == 1:
        return origem == destino
    if alcance == 2:
        return origem != destino
    return False


def descrever_posicao(pos: int) -> str:
    return "Campo de batalha" if pos == 0 else f"Backline do grupo {pos}"


def descrever_alvo(game: 'evento', i: int, j: int, m: creature) -> str:
    """Linha de texto de um alvo possível (i = grupo, j = membro)."""
    vida = f"{m.get_vida()}/{m.get_vida_max()}"
    if m.get_vida_temp() > 0:
        vida += f" (+{m.get_vida_temp()})"
    return (f"{m.nome} | Grupo {game.grupos[i].nome} | Vida {vida} | "
            f"{game.nome_posicao(game.grupos[i].posicao[j])}")


class InterfaceConsole:
    """Todas as perguntas do combate passam por aqui. Esta versão usa o terminal;
    uma GUI troca 'evento.ui' por outro objeto com os mesmos métodos."""

    def escolher_alvo(self, game, cand):
        """cand = [(grupo, membro, criatura)]. Retorna a criatura; levanta Exception se cancelar."""
        print("\nPossíveis alvos:")
        for n, (i, j, m) in enumerate(cand, start=1):
            print(f"  {n} - {descrever_alvo(game, i, j, m)}")
        while True:
            s = ler_int("Qual alvo (0 para cancelar): ")
            if s == 0:
                raise Exception("Ação cancelada")
            try:
                if not 1 <= s <= len(cand):
                    raise Exception("Alvo inválido")
                return cand[s - 1][2]
            except Exception as e:
                print(e)

    def escolher_membro(self, g, game):
        """Retorna 0 para passar o turno ou (índice do membro + 1)."""
        g.listar_membros_ativos(game)
        print("0 - Passar turno (NPCs do grupo agem sozinhos)")
        return ler_int("Qual membro vai realizar a ação: ")

    def acao_jogador(self, game, m, posicao, idx):
        """Menu de ações de um jogador (só retorna quando ele gastou a ação)."""
        m.acao(game, posicao, idx)

    def mudou(self, game):
        """Chamado quando o estado do combate muda (útil para redesenhar a tela)."""
        pass


class evento(ABC):
    grupos: List['grupo']
    grupoAtual: int

    def __init__(self):
        self.grupos = []
        self.grupoAtual = 0
        self.ui = InterfaceConsole()

    def mostrar_grupos(self):
        res = ""
        for i in range(0,len(self.grupos)):
            res += f"{i+1} - Grupo {self.grupos[i].nome}\n"
            for j in range(0,len(self.grupos[i].membros)):
                if self.grupos[i].posicao[j] == 0:
                    loc = "Frontline"
                else: 
                    loc = f"Backline do grupo {self.grupos[self.grupos[i].posicao[j]-1].nome}"
                res += f"{j+1} - Nome: {self.grupos[i].membros[j].nome} | posição: {loc}\n"
        return res

    def adicionar_grupo(self, g: 'grupo'):
        self.grupos.append(g)

    def listar_menbros_grupo(self, i):
        self.grupos[i].listar_membros()

    def reiniciar_ordem(self):
        self.grupoAtual = 0

    def proximo_grupo(self):
        self.grupoAtual += 1

    def atualizar_mortes(self):
        for g in self.grupos:
            g.ver_morreu()
        self.ui.mudou(self)

    def grupos_vivos(self):
        return sum(1 for g in self.grupos if g.verificar_grupo_vivo())

    def combate_em_andamento(self):
        return self.grupos_vivos() >= 2

    def nome_posicao(self, pos: int) -> str:
        if pos == 0:
            return "Campo de batalha"
        if 1 <= pos <= len(self.grupos):
            return f"Backline do grupo {self.grupos[pos - 1].nome}"
        return f"Posição {pos}"

    # ------------------------------------------------------------ alvos
    def _candidatos(self, alcance: int, posicao: int) -> List[Tuple[int, int, creature]]:
        """(índice do grupo, índice do membro, criatura) que o grupo ATUAL pode acertar
        estando em 'posicao' com uma ação de 'alcance'."""
        res = []
        for i, g in enumerate(self.grupos):
            if i == self.grupoAtual:
                continue
            for j, m in enumerate(g.membros):
                if m.esta_vivo() and pode_atingir(alcance, posicao, g.posicao[j]):
                    res.append((i, j, m))
        return res

    def alvos_validos(self, alcance: int, posicao: int) -> List[creature]:
        return [m for _, _, m in self._candidatos(alcance, posicao)]

    def escolher_alvo(self, alcance: int, posicao: int) -> creature:
        """Lista os alvos possíveis e deixa o jogador escolher.
        Levanta Exception se não houver alvo ao alcance (ou Exception se desistir)."""
        cand = self._candidatos(alcance, posicao)
        if not cand:
            raise Exception("Nenhum alvo ao alcance")
        return self.ui.escolher_alvo(self, cand)

    def remover_grupo(self):
        for j, g in enumerate(self.grupos, start=1):
            print(f"grupo {j}: {g.nome}\n")
            self.listar_menbros_grupo(j - 1)
        s = ler_int("Qual vc deseja remover: ")
        if 0 < s <= len(self.grupos):
            self.grupos.pop(s - 1)
        else:
            raise Exception("Fora dos parametros")

    def __str__(self):
        info = f"{type(self).__name__} com {len(self.grupos)} grupo(s)\n"
        for g in self.grupos:
            info += str(g)
        return info


class grupo:
    nome: str
    membros: List[creature]
    posicao: List[int]   # 0 = campo | g+1 = backline do grupo g
    ativo: List[bool]    # ainda pode agir neste turno
    vivo: List[bool]

    def __init__(self, nome):
        self.nome = nome
        self.membros = []
        self.posicao = []
        self.ativo = []
        self.vivo = []

    def adicionar(self, c: creature):
        self.membros.append(c)
        self.ativo.append(True)
        self.posicao.append(0)
        self.vivo.append(True)

    def remover(self):
        if not self.membros:
            raise Exception("Esse grupo não tem membros")
        self.listar_membros()
        s = ler_int("Qual vc deseja remover: ")
        if 0 < s <= len(self.membros):
            self.membros.pop(s - 1)
            self.ativo.pop(s - 1)
            self.posicao.pop(s - 1)
            self.vivo.pop(s - 1)
        else:
            raise Exception("Fora dos parametros")

    def mover(self, idx: int, nova: int):
        self.posicao[idx] = nova

    def realizou(self, idx: int):
        """idx começa em 0."""
        if 0 <= idx < len(self.ativo):
            self.ativo[idx] = False
        else:
            raise Exception("Erro fora dos parametros")

    def ver_morreu(self):
        for j, m in enumerate(self.membros):
            if m.get_vida() > 0:
                self.vivo[j] = True
            else:
                if self.vivo[j]:
                    print(f"{m.nome} caiu!")
                self.vivo[j] = False
                self.ativo[j] = False

    def verificar_grupo_vivo(self):
        return any(self.vivo)

    def novo_turno(self):
        self.ver_morreu()
        for j in range(len(self.ativo)):
            self.ativo[j] = self.vivo[j]

    def definir_posicao(self, idx_grupo: int, game: 'evento'):
        """Cada membro escolhe a posição inicial (classe/arma para humanoides)."""
        for i, m in enumerate(self.membros):
            self.posicao[i] = m.definirPosicao(idx_grupo)
            print(f"  {m.nome} começa em: {game.nome_posicao(self.posicao[i])}")

    def listar_membros(self):
        for j, m in enumerate(self.membros, start=1):
            print(f"Membro {j}: {m.nome}\n")

    def listar_membros_ativos(self, game: Optional['evento'] = None):
        for j, m in enumerate(self.membros):
            local = f" | {game.nome_posicao(self.posicao[j])}" if game else ""
            if not self.vivo[j]:
                estado = "Caído"
            elif isinstance(m, creature_npc):
                estado = "NPC (age sozinho)" if self.ativo[j] else "NPC já agiu"
            elif self.ativo[j]:
                estado = "Com ação disponivel"
            else:
                estado = "Já realizou a ação"
            print(f"Membro {j + 1}: {m.nome} | Vida {m.get_vida()}/{m.get_vida_max()}{local} | {estado}")

    def verificar_atividade(self):
        """True se ainda existe alguém vivo que não agiu."""
        return any(a and v for a, v in zip(self.ativo, self.vivo))

    def tem_jogador_ativo(self):
        return any(a and v and not isinstance(m, creature_npc)
                   for m, a, v in zip(self.membros, self.ativo, self.vivo))

    def turno_npcs(self, game: 'evento'):
        for j, m in enumerate(self.membros):
            if not game.combate_em_andamento():
                break
            if isinstance(m, creature_npc) and self.ativo[j] and self.vivo[j]:
                print(f"\n-- Vez de {m.nome} --")
                m.acao(game, self.posicao[j], j)
                self.realizou(j)
                game.atualizar_mortes()

    def acoes_do_grupo(self, game: 'evento'):
        while self.tem_jogador_ativo() and game.combate_em_andamento():
            try:
                s = game.ui.escolher_membro(self, game)
                if s == 0:
                    break
                if not (1 <= s <= len(self.membros)):
                    raise Exception("Fora dos parametros")
                m = self.membros[s - 1]
                if isinstance(m, creature_npc):
                    raise Exception("Esse membro é um NPC e age automaticamente no fim da vez do grupo")
                if not (self.ativo[s - 1] and self.vivo[s - 1]):
                    raise Exception("Este membro não pode agir (já agiu ou está caído)\n")
                game.ui.acao_jogador(game, m, self.posicao[s - 1], s - 1)
                self.realizou(s - 1)
                game.atualizar_mortes()
            except Exception as e:
                print(e)
        self.turno_npcs(game)
        game.proximo_grupo()

    def __str__(self):
        info = f"Grupo {self.nome} ({len(self.membros)} membro(s))\n"
        for j, m in enumerate(self.membros):
            tipo = "NPC" if isinstance(m, creature_npc) else "Player"
            estado = "vivo" if self.vivo[j] else "caído"
            info += (f"  {j + 1} - {m.nome} [{tipo}] | Vida {m.get_vida()}/{m.get_vida_max()} | "
                     f"{descrever_posicao(self.posicao[j])} | {estado}\n")
        return info


LIMITE_EMPATE = 20   # turnos seguidos sem ninguém perder vida (só vale sem jogadores vivos)


class combate(evento):
    turno: int

    def __init__(self):
        super().__init__()
        self.turno = 1
        self._ultimo_total = None
        self._sem_dano = 0

    def travado(self):
        """Impasse: ninguém perde vida há LIMITE_EMPATE turnos e só há NPCs vivos
        (ex.: dois arqueiros que não conseguem se acertar)."""
        total = sum(m.get_vida() + m.get_vida_temp() for gr in self.grupos for m in gr.membros)
        self._sem_dano = self._sem_dano + 1 if total == self._ultimo_total else 0
        self._ultimo_total = total
        ha_jogador = any(v and not isinstance(m, creature_npc)
                         for gr in self.grupos for m, v in zip(gr.membros, gr.vivo))
        return not ha_jogador and self._sem_dano >= LIMITE_EMPATE

    def passar_turno(self):
        self.reiniciar_ordem()
        self.turno += 1
        for g in self.grupos:
            g.novo_turno()

    def preparar_combate(self):
        for i, g in enumerate(self.grupos):
            print(f"Grupo {g.nome}:")
            g.definir_posicao(i, self)

    def comecar_combate(self):
        for gr in self.grupos:
            gr.novo_turno()          # zera 'ativo' e confere quem caiu (vale para combate repetido)
        self.reiniciar_ordem()
        self.atualizar_mortes()
        empate = False
        while self.combate_em_andamento():
            print(f"\n===== Turno {self.turno} =====")
            self.reiniciar_ordem()
            while self.grupoAtual < len(self.grupos) and self.combate_em_andamento():
                gr = self.grupos[self.grupoAtual]
                print(f"\n--- Grupo {gr.nome} ---")
                if gr.verificar_grupo_vivo():
                    gr.acoes_do_grupo(self)   # já avança o grupoAtual no fim
                else:
                    print(f"Turno do grupo {gr.nome} anulado: todos caíram")
                    self.proximo_grupo()
            if self.combate_em_andamento():
                self.passar_turno()
                if self.travado():
                    empate = True
                    break
        if empate:
            print("\nFim do combate por impasse: ninguém consegue ferir o outro (empate).")
            return
        vencedores = [gr.nome for gr in self.grupos if gr.verificar_grupo_vivo()]
        if vencedores:
            print(f"\nFim do combate! Vencedor: {vencedores[0]}")
        else:
            print("\nFim do combate! Todos caíram.")

    def __str__(self):
        return f"Combate (turno {self.turno})\n" + super().__str__()
