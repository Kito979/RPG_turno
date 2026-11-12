import queue
import threading
import tkinter as tk
from contextlib import redirect_stdout
from tkinter import ttk, messagebox, simpledialog

from Classes import cavaleiro, xama, sentinela
from Racas import Besouro
from Equipamentos import Espada, Arco
from Creature import creature_npc
from Game import grupo, combate, descrever_alvo
from Humanoid import player, humanoidNPC

CLASSES = {"Cavaleiro": cavaleiro, "Xamã": xama, "Sentinela": sentinela}
RACAS = {"Besouro": Besouro}
ARMAS = {"Nenhuma": None, "Espada": Espada, "Arco": Arco}
STATUS = ["seiva", "quitina", "ferroada", "reflexo", "alma"]
PONTOS = 12


class DialogoPersonagem(tk.Toplevel):
    """Formulário de criação. npc=False cria um player; npc=True cria um humanoidNPC."""

    def __init__(self, app, npc):
        super().__init__(app.root)
        self.app, self.npc = app, npc
        self.title("Novo NPC" if npc else "Novo jogador")
        self.resizable(False, False)
        self.transient(app.root)
        self.wait_visibility()   # no Linux o grab falha se a janela ainda não apareceu
        self.grab_set()

        f = ttk.Frame(self, padding=12)
        f.grid()
        r = 0
        self.nome = tk.StringVar()
        self.jogador = tk.StringVar()
        self.grupo = tk.StringVar()
        self.classe = tk.StringVar(value="Cavaleiro")
        self.raca = tk.StringVar(value="Besouro")
        self.arma = tk.StringVar(value="Espada")
        self.stats = {k: tk.IntVar(value=1) for k in STATUS}

        def linha(rotulo, widget):
            nonlocal r
            ttk.Label(f, text=rotulo).grid(row=r, column=0, sticky="w", pady=2)
            widget.grid(row=r, column=1, sticky="ew", pady=2)
            r += 1

        linha("Personagem:", ttk.Entry(f, textvariable=self.nome))
        if not npc:
            linha("Jogador:", ttk.Entry(f, textvariable=self.jogador))
        nomes_grupos = [g.nome for g in app.grupos]
        self.grupo.set(nomes_grupos[0] if nomes_grupos else "")
        linha("Grupo:", ttk.Combobox(f, textvariable=self.grupo, values=nomes_grupos, state="readonly"))
        linha("Classe:", ttk.Combobox(f, textvariable=self.classe, values=list(CLASSES), state="readonly"))
        linha("Raça:", ttk.Combobox(f, textvariable=self.raca, values=list(RACAS), state="readonly"))
        linha("Arma:", ttk.Combobox(f, textvariable=self.arma, values=list(ARMAS), state="readonly"))

        ttk.Separator(f).grid(row=r, columnspan=2, sticky="ew", pady=6)
        r += 1
        for k in STATUS:
            sp = ttk.Spinbox(f, from_=1, to=5, width=5, textvariable=self.stats[k], command=self.atualizar)
            sp.bind("<KeyRelease>", lambda e: self.atualizar())
            linha(k.capitalize() + ":", sp)
        self.restante = ttk.Label(f)
        self.restante.grid(row=r, columnspan=2, pady=4)
        r += 1
        ttk.Button(f, text="Criar", command=self.criar).grid(row=r, column=0, pady=6)
        ttk.Button(f, text="Cancelar", command=self.destroy).grid(row=r, column=1, pady=6)
        self.atualizar()

    def valores(self):
        try:
            return {k: v.get() for k, v in self.stats.items()}
        except tk.TclError:
            return None

    def atualizar(self):
        v = self.valores()
        if v is None:
            self.restante.config(text="Use apenas números")
            return
        self.restante.config(text=f"Pontos restantes: {PONTOS - sum(v.values())} (cada status de 1 a 5)")

    def criar(self):
        v = self.valores()
        if v is None or sum(v.values()) != PONTOS or not all(1 <= x <= 5 for x in v.values()):
            messagebox.showwarning("Status inválidos",
                                   f"Distribua exatamente {PONTOS} pontos, com cada status entre 1 e 5.", parent=self)
            return
        nome = self.nome.get().strip()
        if not nome or not self.grupo.get():
            messagebox.showwarning("Faltam dados", "Informe o nome e o grupo.", parent=self)
            return
        classe, raca = CLASSES[self.classe.get()](), RACAS[self.raca.get()]()
        arma = ARMAS[self.arma.get()]
        arma = arma() if arma else None
        args = dict(seiva=v["seiva"], quitina=v["quitina"], ferroada=v["ferroada"],
                    reflexo=v["reflexo"], alma=v["alma"], nome=nome)
        if self.npc:
            c = humanoidNPC(raca, 1, classe, arma=arma, **args)
        else:
            c = player(self.jogador.get().strip() or "?", raca=raca, classeh=classe, **args)
            if arma:
                c.adicionar_item(arma)
        self.app.adicionar(self.grupo.get(), c)
        self.destroy()


ABORTAR = object()   # resposta especial: a janela foi fechada no meio do combate


class CombateAbortado(BaseException):
    pass


class Saida:
    """Substitui o print() durante o combate: o texto vai para o log da janela."""

    def __init__(self, fila):
        self.fila = fila

    def write(self, s):
        if s:
            self.fila.put(("log", s))
        return len(s)

    def flush(self):
        pass


class InterfaceGrafica:
    """Versão com botões da InterfaceConsole (Game.py). Roda na thread do combate;
    cada pergunta é repassada para a thread da janela e a resposta volta pela fila."""

    def __init__(self, janela):
        self.j = janela

    def _gui(self, fn, *args):
        q = queue.Queue()
        if self.j.fechando:
            raise CombateAbortado()
        self.j.fila.put(("req", fn, args, q))
        while True:
            try:
                r = q.get(timeout=0.2)
                break
            except queue.Empty:
                if self.j.fechando:
                    raise CombateAbortado()
        if r is ABORTAR:
            raise CombateAbortado()
        return r

    def escolher(self, titulo, textos, cancelavel=False):
        return self._gui(self.j.perguntar, titulo, textos, cancelavel)

    def escolher_alvo(self, game, cand):
        i = self.escolher("Escolha o alvo", [descrever_alvo(game, *c) for c in cand], True)
        if i is None:
            raise Exception("Ação cancelada")
        return cand[i][2]

    def escolher_membro(self, g, game):
        idx = [j for j, m in enumerate(g.membros)
               if g.ativo[j] and g.vivo[j] and not isinstance(m, creature_npc)]
        textos = [f"{g.membros[j].nome} (vida {g.membros[j].get_vida()}/{g.membros[j].get_vida_max()})"
                  for j in idx]
        i = self.escolher(f"Grupo {g.nome}: quem age?", textos + ["Passar turno"])
        return 0 if i == len(idx) else idx[i] + 1

    def mudou(self, game):
        self.j.fila.put(("estado", str(game)))

    def acao_jogador(self, game, m, posicao, idx):
        andou = False
        while True:
            cab = (f"{m.nome} | Vida {m.get_vida()}/{m.get_vida_max()} | Vigor {m.get_vg()} | "
                   f"Sanidade {m.get_snd()} | {game.nome_posicao(posicao)}")
            s = self.escolher(cab, ["Atacar", "Trocar arma principal", "Usar item", "Usar habilidade",
                                    "Avançar", "Recuar", "Meditar"])
            try:
                if s == 0:
                    m.atacar(game, posicao)
                    return
                elif s == 1:
                    armas = [(i, it) for i, it in enumerate(m.inventariro) if it.get_tipo() == 1]
                    if not armas:
                        raise Exception("Nenhuma arma no inventário")
                    k = self.escolher("Qual arma equipar", [it.nome for _, it in armas], True)
                    if k is None:
                        raise Exception("Ação cancelada")
                    m.arma_atual = armas[k][0]
                    return
                elif s == 2:
                    itens = [(i, it) for i, it in enumerate(m.inventariro) if it.get_tipo() in (2, 3, 4)]
                    if not itens:
                        raise Exception("Nenhum item utilizável")
                    k = self.escolher("Qual item usar", [f"{it.nome} (x{it.qntd})" for _, it in itens], True)
                    if k is None:
                        raise Exception("Ação cancelada")
                    i, it = itens[k]
                    it.verusar(game, m, posicao)
                    if it.qntd <= 0:
                        m.inventariro.pop(i)
                        if m.arma_atual > i:
                            m.arma_atual -= 1
                    return
                elif s == 3:
                    sks = m.todas_skills()
                    if not sks:
                        raise Exception("Nenhuma habilidade")
                    k = self.escolher("Qual habilidade usar", [str(sk).split("\n")[0] for sk in sks], True)
                    if k is None:
                        raise Exception("Ação cancelada")
                    sks[k].cogitar(game, posicao, m)
                    return
                elif s in (4, 5):
                    if andou:
                        raise Exception("Você já andou nesse turno")
                    nova = posicao
                    if s == 4:
                        ds = m.destinos_avanco(game, posicao)
                        if len(ds) == 1:
                            nova = ds[0]
                        elif ds:
                            k = self.escolher("Avançar até onde", [game.nome_posicao(d) for d in ds], True)
                            if k is None:
                                raise Exception("Ação cancelada")
                            nova = ds[k]
                    else:
                        nova = m.destino_recuo(game, posicao)
                    if nova == posicao:
                        raise Exception("Você não pode se mover nessa direção")
                    game.grupos[game.grupoAtual].mover(idx, nova)
                    posicao, andou = nova, True
                    print(f"{m.nome} agora está em: {game.nome_posicao(nova)}")
                    self.mudou(game)
                else:
                    m.meditar()
                    return
            except Exception as e:
                print(e)


class JanelaCombate(tk.Toplevel):
    """Tela do combate: estado dos grupos, log e botões de escolha. Sem animação."""

    def __init__(self, app, game):
        super().__init__(app.root)
        self.app, self.game = app, game
        self.title("Combate")
        self.geometry("780x640")
        self.fila = queue.Queue()
        self.escolha = tk.IntVar(value=-3)
        self.fechando = False
        self.terminou = False

        self.estado = tk.Text(self, height=13, state="disabled", font=("Consolas", 9))
        self.estado.pack(fill="x")
        self.log = tk.Text(self, height=12, state="disabled", wrap="word", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self.titulo = ttk.Label(self, anchor="w", font=("TkDefaultFont", 10, "bold"))
        self.titulo.pack(fill="x", padx=6, pady=(6, 0))
        self.botoes = ttk.Frame(self)
        self.botoes.pack(fill="x", padx=6, pady=6)

        self.protocol("WM_DELETE_WINDOW", self.fechar)
        game.ui = InterfaceGrafica(self)
        self.after(40, self.bombear)
        threading.Thread(target=self.rodar, daemon=True).start()

    def rodar(self):
        try:
            with redirect_stdout(Saida(self.fila)):
                self.game.preparar_combate()
                self.game.comecar_combate()
        except CombateAbortado:
            pass
        except Exception:
            import traceback
            self.fila.put(("log", "\nERRO NO COMBATE:\n" + traceback.format_exc()))
        finally:
            self.fila.put(("fim",))

    def bombear(self):
        """Roda na thread da janela: mostra logs/estado e atende as perguntas do combate."""
        if self.fechando:
            return
        while True:
            if self.fechando:
                return
            try:
                item = self.fila.get_nowait()
            except queue.Empty:
                break
            if item[0] == "log":
                self.escrever(self.log, item[1], True)
            elif item[0] == "estado":
                self.escrever(self.estado, item[1])
            elif item[0] == "fim":
                self.terminou = True
                self.limpar()
                self.titulo.config(text="Combate encerrado.")
                ttk.Button(self.botoes, text="Fechar", command=self.fechar).pack(fill="x")
            else:
                _, fn, args, q = item
                try:
                    q.put(fn(*args))
                except Exception:
                    import traceback
                    traceback.print_exc()
                    q.put(ABORTAR)
        if not self.fechando:
            self.after(40, self.bombear)

    def escrever(self, w, txt, anexar=False):
        w.config(state="normal")
        if not anexar:
            w.delete("1.0", "end")
        w.insert("end", txt)
        if anexar:
            w.see("end")
        w.config(state="disabled")

    def limpar(self):
        for w in self.botoes.winfo_children():
            w.destroy()

    def perguntar(self, titulo, textos, cancelavel):
        if self.fechando:
            return ABORTAR
        self.titulo.config(text=titulo)
        self.limpar()
        for i, t in enumerate(textos):
            ttk.Button(self.botoes, text=t, command=lambda i=i: self.escolha.set(i)).pack(fill="x", pady=1)
        if cancelavel:
            ttk.Button(self.botoes, text="Cancelar", command=lambda: self.escolha.set(-1)).pack(fill="x", pady=1)
        self.escolha.set(-3)
        self.wait_variable(self.escolha)
        if self.fechando:
            return ABORTAR
        r = self.escolha.get()
        self.limpar()
        self.titulo.config(text="")
        return None if r == -1 else r

    def fechar(self):
        if not self.terminou and not messagebox.askyesno("Combate", "Encerrar o combate em andamento?", parent=self):
            return
        self.fechando = True
        self.escolha.set(-2)    # destrava uma pergunta pendente
        self.app.combate_aberto = None
        self.destroy()
        self.app.atualizar("Combate encerrado.")


class App:
    def __init__(self, root):
        self.root = root
        self.grupos = []
        self.combate_aberto = None
        self.combate_terminal = None
        root.title("Combate RPG")
        root.geometry("820x520")
        self.montar_menu()

        painel = ttk.PanedWindow(root, orient="horizontal")
        painel.pack(fill="both", expand=True)
        self.arvore = ttk.Treeview(painel, show="tree", selectmode="browse")
        self.arvore.bind("<<TreeviewSelect>>", lambda e: self.mostrar())
        painel.add(self.arvore, weight=1)
        self.texto = tk.Text(painel, state="disabled", wrap="word", font=("Consolas", 10))
        painel.add(self.texto, weight=2)
        self.status = ttk.Label(root, anchor="w", relief="sunken")
        self.status.pack(fill="x")
        self.atualizar()

    # ------------------------------------------------------------ menu
    def montar_menu(self):
        mb = tk.Menu(self.root)
        m = tk.Menu(mb, tearoff=0)
        m.add_command(label="Novo grupo...", command=self.novo_grupo)
        m.add_separator()
        m.add_command(label="Jogador...", command=lambda: self.abrir(False))
        m.add_command(label="NPC (manual)...", command=lambda: self.abrir(True))
        m.add_command(label="NPC aleatório...", command=self.npc_aleatorio)
        mb.add_cascade(label="Criar", menu=m)

        m = tk.Menu(mb, tearoff=0)
        m.add_command(label="Remover selecionado", command=self.remover)
        mb.add_cascade(label="Editar", menu=m)

        m = tk.Menu(mb, tearoff=0)
        m.add_command(label="Iniciar combate (visual)", command=lambda: self.iniciar_combate(True))
        m.add_command(label="Iniciar combate (terminal)", command=lambda: self.iniciar_combate(False))
        m.add_command(label="Restaurar vida de todos", command=self.restaurar)
        m.add_separator()
        m.add_command(label="Sair", command=self.root.destroy)
        mb.add_cascade(label="Combate", menu=m)
        self.root.config(menu=mb)

    # ------------------------------------------------------------ criação
    def achar_grupo(self, nome):
        return next(g for g in self.grupos if g.nome == nome)

    def em_combate(self):
        """Impede mexer em grupos/personagens enquanto há combate rodando."""
        aberto = self.combate_aberto and not self.combate_aberto.terminou
        terminal = self.combate_terminal and self.combate_terminal.is_alive()
        if aberto or terminal:
            messagebox.showinfo("Combate em andamento", "Termine o combate antes de alterar grupos e personagens.")
            return True
        return False

    def novo_grupo(self):
        if self.em_combate():
            return
        nome = simpledialog.askstring("Novo grupo", "Nome do grupo:", parent=self.root)
        if not nome or not nome.strip():
            return
        if any(g.nome == nome.strip() for g in self.grupos):
            messagebox.showwarning("Grupo existente", "Já existe um grupo com esse nome.")
            return
        self.grupos.append(grupo(nome.strip()))
        self.atualizar()

    def abrir(self, npc):
        if self.em_combate():
            return
        if not self.grupos:
            messagebox.showinfo("Sem grupo", "Crie um grupo primeiro (Criar > Novo grupo).")
            return
        DialogoPersonagem(self, npc)

    def npc_aleatorio(self):
        if self.em_combate():
            return
        if not self.grupos:
            messagebox.showinfo("Sem grupo", "Crie um grupo primeiro (Criar > Novo grupo).")
            return
        d = tk.Toplevel(self.root)
        d.title("NPC aleatório")
        d.transient(self.root)
        d.wait_visibility()
        d.grab_set()
        d.resizable(False, False)
        f = ttk.Frame(d, padding=12)
        f.grid()
        g = tk.StringVar(value=self.grupos[0].nome)
        n = tk.IntVar(value=1)
        q = tk.IntVar(value=1)
        ttk.Label(f, text="Grupo:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Combobox(f, textvariable=g, values=[x.nome for x in self.grupos],
                     state="readonly").grid(row=0, column=1, pady=2)
        ttk.Label(f, text="Nível:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Spinbox(f, from_=1, to=20, width=5, textvariable=n).grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(f, text="Quantidade:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Spinbox(f, from_=1, to=10, width=5, textvariable=q).grid(row=2, column=1, sticky="w", pady=2)

        def ok():
            try:
                lvl, qtd = n.get(), q.get()
            except tk.TclError:
                return
            for _ in range(qtd):
                self.adicionar(g.get(), humanoidNPC.aleatorio(lvl))
            d.destroy()

        ttk.Button(f, text="Criar", command=ok).grid(row=3, column=0, pady=8)
        ttk.Button(f, text="Cancelar", command=d.destroy).grid(row=3, column=1, pady=8)

    def adicionar(self, nome_grupo, criatura):
        self.achar_grupo(nome_grupo).adicionar(criatura)
        self.atualizar(f"{criatura.nome} criado no grupo {nome_grupo}.")

    def remover(self):
        if self.em_combate():
            return
        sel = self.arvore.selection()
        if not sel:
            return
        iid = sel[0]
        gi, _, mi = iid[1:].partition("m")
        gi = int(gi)
        if mi == "":
            if messagebox.askyesno("Remover", f"Remover o grupo {self.grupos[gi].nome} inteiro?"):
                self.grupos.pop(gi)
        else:
            g, mi = self.grupos[gi], int(mi)
            for lista in (g.membros, g.ativo, g.posicao, g.vivo):
                lista.pop(mi)
        self.atualizar()

    # ------------------------------------------------------------ combate
    def iniciar_combate(self, visual=True):
        if self.combate_aberto:
            self.combate_aberto.lift()
            return
        if self.combate_terminal and self.combate_terminal.is_alive():
            messagebox.showinfo("Combate", "Já há um combate rodando no terminal.")
            return
        com_membros = [g for g in self.grupos if g.membros]
        if sum(g.verificar_grupo_vivo() for g in com_membros) < 2:
            messagebox.showinfo("Combate", "Precisa de pelo menos 2 grupos com membros vivos "
                                           "(Combate > Restaurar vida de todos, se já lutaram).")
            return
        c = combate()
        for g in com_membros:
            c.adicionar_grupo(g)
        if visual:
            self.combate_aberto = JanelaCombate(self, c)
            return
        messagebox.showinfo("Combate", "O combate roda no terminal (entradas por input). "
                                       "Acompanhe lá; esta janela continua aberta.")

        def rodar():
            c.preparar_combate()
            c.comecar_combate()

        self.combate_terminal = threading.Thread(target=rodar, daemon=True)
        self.combate_terminal.start()

    def restaurar(self):
        if self.em_combate():
            return
        for g in self.grupos:
            for j, m in enumerate(g.membros):
                m.restaurar()
                g.vivo[j] = g.ativo[j] = True
        self.atualizar("Vida, vigor e sanidade restaurados.")

    # ------------------------------------------------------------ exibição
    def atualizar(self, msg=""):
        self.arvore.delete(*self.arvore.get_children())
        for gi, g in enumerate(self.grupos):
            self.arvore.insert("", "end", iid=f"g{gi}", text=f"Grupo {g.nome} ({len(g.membros)})", open=True)
            for mi, m in enumerate(g.membros):
                tipo = "NPC" if isinstance(m, humanoidNPC) else "Player"
                self.arvore.insert(f"g{gi}", "end", iid=f"g{gi}m{mi}", text=f"{m.nome} [{tipo}]")
        self.status.config(text=msg or f"{len(self.grupos)} grupo(s)")
        self.escrever("")

    def mostrar(self):
        sel = self.arvore.selection()
        if not sel:
            return
        gi, _, mi = sel[0][1:].partition("m")
        g = self.grupos[int(gi)]
        self.escrever(str(g) if mi == "" else str(g.membros[int(mi)]))

    def escrever(self, txt):
        self.texto.config(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", txt)
        self.texto.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
