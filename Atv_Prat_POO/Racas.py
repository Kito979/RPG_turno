from __future__ import annotations
from abc import ABC
from typing import List, TYPE_CHECKING

from Utils import ler_int

if TYPE_CHECKING:
    from Habilidades import skill
    from Humanoid import humanoid

qnt_raca = 1


class raca(ABC):
    _vtbase: int
    _vgbase: int
    _sndbase: int
    skills: List[skill]

    def __init__(self, vt=1, vg=1, snd=1):
        self._vtbase = vt
        self._vgbase = vg
        self._sndbase = snd
        self.skills = []

    def get_vt_base(self):
        return self._vtbase

    def get_vg_base(self):
        return self._vgbase

    def get_snd_base(self):
        return self._sndbase

    def adicionar_skill(self, sk: skill):
        self.skills.append(sk)

    def lvl_up(self, user: humanoid):
        pass

    def remover_skill(self):
        try:
            if not self.skills:
                raise Exception("Essa raça não tem skills")
            print("Skills:\n")
            for j, sk in enumerate(self.skills, start=1):
                print(f"{j} = {sk.nome}\n")
            s = ler_int("Qual skill será removida: ")
            if not 0 < s <= len(self.skills):
                raise Exception("Skill inválida")
            self.skills.pop(s - 1)
        except Exception as e:
            print(e)

    def __str__(self):
        info = f"Raça: {type(self).__name__}\n"
        info += f"Base -> Vitalidade {self._vtbase} | Vigor {self._vgbase} | Sanidade {self._sndbase}\n"
        if self.skills:
            info += "Skills de raça: " + ", ".join(sk.nome for sk in self.skills) + "\n"
        else:
            info += "Skills de raça: nenhuma\n"
        return info


class Besouro(raca):
    def __init__(self, vt=3, vg=1, snd=2):
        super().__init__(vt, vg, snd)

    def lvl_up(self, user: humanoid):
        # Skills de raça por nível entram aqui: case 2: self.adicionar_skill(...)
        match user.lvl:
            case _:
                pass
        return super().lvl_up(user)
