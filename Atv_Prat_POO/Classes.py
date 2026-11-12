from __future__ import annotations
from abc import ABC
from typing import Dict, List, Tuple, TYPE_CHECKING

from Habilidades import *

if TYPE_CHECKING:
    from Humanoid import humanoid

qnt_classe = 3


class classe(ABC):
    _vt_base: int   # vt = vitalidade/vida; se zerar cai
    _vg_base: int   # vg = vigor; usado nas skills (cada skill tem um custo)
    _snd_base: int  # snd = sanidade; também custa skills e é outra forma de levar dano
    skills: List[skill]
    fica_na_frente: bool                # posição padrão quando está desarmado
    perfil: Dict[str, Tuple[int, int]]  # faixas de atributos para fichas aleatórias

    def __init__(self, vt_base, vg_base, snd_base, fica_na_frente=True, perfil=None):
        self._vt_base = vt_base
        self._vg_base = vg_base
        self._snd_base = snd_base
        self.fica_na_frente = fica_na_frente
        self.perfil = perfil or {}
        self.skills = []

    def get_vt_base(self):
        return self._vt_base

    def get_vg_base(self):
        return self._vg_base

    def get_snd_base(self):
        return self._snd_base

    def lvl_up(self, user: humanoid):
        pass

    def adicionar_skill(self, sk: skill):
        self.skills.append(sk)

    def __str__(self):
        info = f"Classe: {type(self).__name__}\n"
        info += f"Base -> Vitalidade {self._vt_base} | Vigor {self._vg_base} | Sanidade {self._snd_base}\n"
        info += f"Posição padrão desarmado: {'frente (campo)' if self.fica_na_frente else 'backline'}\n"
        if self.skills:
            info += "Skills de classe: " + ", ".join(sk.nome for sk in self.skills) + "\n"
        else:
            info += "Skills de classe: nenhuma\n"
        return info


class cavaleiro(classe):
    def __init__(self):
        super().__init__(vt_base=3, vg_base=2, snd_base=1, fica_na_frente=True,
                         perfil={"seiva": (1, 2), "quitina": (3, 3), "ferroada": (2, 3),
                                 "reflexo": (1, 2), "alma": (1, 1)})
        self.adicionar_skill(skill_golpe_de_foco_absoluto())
    def lvl_up(self, user):
        match user.lvl:
            case 2:
                self.adicionar_skill(skill_disparo_de_foco_absoluto())
            case _:
                pass
        return super().lvl_up(user)


class xama(classe):
    def __init__(self):
        super().__init__(vt_base=1, vg_base=1, snd_base=4, fica_na_frente=False,
                         perfil={"seiva": (1, 2), "quitina": (1, 1), "ferroada": (1, 1),
                                 "reflexo": (2, 3), "alma": (3, 3)})
        self.adicionar_skill(skill_disparo_de_foco_absoluto())


class sentinela(classe):
    def __init__(self):
        super().__init__(vt_base=2, vg_base=3, snd_base=1, fica_na_frente=True,
                         perfil={"seiva": (1, 2), "quitina": (1, 2), "ferroada": (2, 3),
                                 "reflexo": (3, 3), "alma": (1, 1)})
        self.adicionar_skill(skill_golpe_de_foco_absoluto())
