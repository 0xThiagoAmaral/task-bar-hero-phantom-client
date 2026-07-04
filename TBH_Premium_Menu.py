import customtkinter as ctk
import pywinstyles
from tkinter import messagebox
import threading
import time
import pymem
import pymem.process
import pymem.pattern
import struct
import psutil
import json
import os
import base64
import tempfile

ICON_B64 = b"AAABAAEAQEAAAAAAIAA0AQAAFgAAAIlQTkcNChoKAAAADUlIRFIAAABAAAAAQAgGAAAAqmlx3gAAAPtJREFUeJzt27Fxw0AMBdHljmtRO8pdoGO7QrkCO7BwR3HWL9UM/gGEkqN0fN4eD8IkTuIkTuIkTuIkTuIkTuIkTuIkTuIk7u2M0DsfP372xfvWsxy7LkR+a/rMYRyrB/CXxncOwldvfrLOtg24Lzzw9DZ4peZX1Jc4r/T0V+R4tean8yTOKz79yVyJkzivuv5T+RIncRIncRIncT5bYPcd3nS+xEmcE0XO+hpM5EqcU4V2b8FUngzaNYTJHIlzuuDqLZiuf6x8NTZ5V7BqsLLQ1KFXbtXx/3b4tv//AsnfB7wqiZM4iZM4iZM4iZM4iZM4iZM4ifPsA5ztGy4tPRsn3vGVAAAAAElFTkSuQmCC"

# ==============================================================================
# ENGINE MEMORY CONFIG
# ==============================================================================
PROCESS_NAME = "TaskBarHero.exe"
MODULE_NAME  = "GameAssembly.dll"
AOB_PATTERN = b"\x48\x8B\x05.{4}\x83\xB8\xE4\x00\x00\x00\x00\x75.\x48\x8B\xC8\xE8.{4}\x48\x8B\x05.{4}\x48\x8B\x80\xB8\x00\x00\x00\x48\x8B\x48\x20\x48\x85\xC9\x74.\x48\x8B\x15.{4}\xE8"

OFFSETS_CHAIN = [0xB8, 0x40, 0x10, 0x20, 0x18]
STAT_OFFSETS = {
    "Attack Damage": 0x3C,
    "Attack Speed":  0x4C,
    "Max HP":        0x7C,
    "Move Speed":    0x9C
}

# ==============================================================================
# PROCESS FINDER
# ==============================================================================
def find_all_processes(process_name=PROCESS_NAME):
    """Encontra todos os PIDs do processo alvo (incluindo sandboxes)."""
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'].lower() == process_name.lower():
                pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids

# ==============================================================================
# HACK ENGINE
# ==============================================================================
class TbhHackEngine:
    def __init__(self, pid):
        self.pid = pid
        self.pm = None
        self.module = None
        self.pstat_base = None
        self.running = False
        self.active_hacks = {
            "Attack Damage": False,
            "Attack Speed": False,
            "Max HP": False,
            "Move Speed": False
        }
        self.hack_values = {
            "Attack Damage": 99999999.0,
            "Max HP":        99999999.0,
            "Attack Speed":  20000.0,    
            "Move Speed":    800.0      
        }
        self.connected = False
        self.status_text = f"PID {pid}: Aguardando..."

    def connect(self):
        try:
            self.pm = pymem.Pymem(self.pid)
            self.module = pymem.process.module_from_name(self.pm.process_handle, MODULE_NAME)
            self.connected = True
            self.status_text = f"PID {self.pid}: Conectado"
            return True, self.status_text
        except Exception as e:
            self.status_text = f"PID {self.pid}: ERRO - {e}"
            return False, self.status_text

    def scan_aob(self):
        if not self.pm or not self.module:
            return False, "Nao conectado."
        address = pymem.pattern.pattern_scan_module(self.pm.process_handle, self.module, AOB_PATTERN)
        if not address:
            self.status_text = f"PID {self.pid}: Pattern nao encontrado"
            return False, self.status_text
        offset_bytes = self.pm.read_bytes(address + 3, 4)
        relative_offset = struct.unpack('<i', offset_bytes)[0]
        self.pstat_base = address + 7 + relative_offset
        self.status_text = f"PID {self.pid}: PRONTO (Base: {hex(self.pstat_base)})"
        return True, self.status_text

    def _get_final_pointer(self):
        if not self.pstat_base: return 0
        try:
            addr = self.pm.read_longlong(self.pstat_base)
            for offset in OFFSETS_CHAIN:
                addr = self.pm.read_longlong(addr + offset)
            return addr
        except:
            return 0

    def hack_loop(self, get_speeds_callback):
        self.running = True
        while self.running:
            ptr = self._get_final_pointer()
            if ptr != 0:
                atk_spd, move_spd = get_speeds_callback()
                self.hack_values["Attack Speed"] = float(atk_spd)
                self.hack_values["Move Speed"] = float(move_spd)
                
                for stat_name, is_active in self.active_hacks.items():
                    if is_active:
                        try:
                            stat_addr = ptr + STAT_OFFSETS[stat_name]
                            self.pm.write_float(stat_addr, float(self.hack_values[stat_name]))
                        except:
                            pass
            time.sleep(0.1)

# ==============================================================================
# GUI
# ==============================================================================
class HackApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Phantom Client [MULTI-INSTANCIA]")
        self.geometry("850x580")
        self.attributes("-topmost", True)
        
        # Tema Moderno
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Icone
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ico") as tmp:
                tmp.write(base64.b64decode(ICON_B64))
                tmp.flush()
                self.iconbitmap(tmp.name)
        except:
            pass
        
        # Aplicar efeito Mica (Vidro/Neon)
        try:
            pywinstyles.apply_style(self, "mica")
        except:
            pass

        self.engines = []
        self.config_file = "farm_config.json"
        
        # Colors - Neon Pink/Purple theme
        self.bg_color = "#0a0a0c"
        self.card_bg = "#16151a"
        self.accent_color = "#b026ff" # Purple
        self.accent_hover = "#ff26a5" # Pink
        self.text_color = "#ffffff"
        self.sub_text = "#8a8a93"
        
        self.configure(fg_color=self.bg_color)
        self.config_data = self.load_config()

        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR (Esquerda) ---
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=self.card_bg)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        # Titulo Sidebar
        self.logo_label = ctk.CTkLabel(self.sidebar, text="TBH PREMIUM", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=self.accent_color)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 5))
        
        self.version_label = ctk.CTkLabel(self.sidebar, text="v3.0 Multi-Instance", font=ctk.CTkFont(size=12), text_color=self.sub_text)
        self.version_label.grid(row=1, column=0, padx=20, pady=(0, 30))

        # Status
        self.lbl_status = ctk.CTkLabel(self.sidebar, text="Aguardando conexão...", font=ctk.CTkFont(size=14), text_color=self.sub_text)
        self.lbl_status.grid(row=2, column=0, padx=20, pady=10)

        # Botão Conectar
        self.btn_connect = ctk.CTkButton(self.sidebar, text="INJETAR", command=self.do_connect, fg_color=self.accent_color, hover_color=self.accent_hover, font=ctk.CTkFont(size=15, weight="bold"), height=45)
        self.btn_connect.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # Lista de instâncias
        self.instances_box = ctk.CTkTextbox(self.sidebar, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#0e0e11", text_color="#aaaaaa", corner_radius=8, wrap="word")
        self.instances_box.grid(row=4, column=0, padx=20, pady=20, sticky="nsew")
        self.add_log("Instancias detectadas aparecerão aqui...")

        # Botão Rescan
        self.btn_rescan = ctk.CTkButton(self.sidebar, text="RE-ESCANEAR", command=self.rescan_instances, fg_color="transparent", border_width=1, text_color=self.text_color, border_color=self.sub_text, hover_color="#222222")
        self.btn_rescan.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")

        # --- MAIN AREA (Direita) ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Header Main
        self.header_label = ctk.CTkLabel(self.main_frame, text="Hacks & Settings", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=self.text_color)
        self.header_label.grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Toggles Frame (Cards)
        self.hacks_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.hacks_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        self.hacks_frame.grid_columnconfigure(0, weight=1)
        self.hacks_frame.grid_columnconfigure(1, weight=1)

        self.vars = {}
        hacks = [
            ("God Mode", "HP Infinito (99.9M)", "Max HP"),
            ("Insta Kill", "Dano Maximo (99.9M)", "Attack Damage"),
            ("Atk Speed", "Sobrescrever Atk Speed", "Attack Speed"),
            ("Move Speed", "Sobrescrever Move Speed", "Move Speed")
        ]
        
        row_idx = 0
        col_idx = 0
        for title, desc, stat_name in hacks:
            card = ctk.CTkFrame(self.hacks_frame, fg_color=self.card_bg, corner_radius=10)
            card.grid(row=row_idx, column=col_idx, padx=(0, 15) if col_idx == 0 else (15, 0), pady=(0, 15), sticky="ew")
            
            lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=16, weight="bold"), text_color=self.text_color)
            lbl_title.pack(anchor="w", padx=15, pady=(15, 0))
            
            lbl_desc = ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=12), text_color=self.sub_text)
            lbl_desc.pack(anchor="w", padx=15, pady=(0, 15))
            
            var = ctk.BooleanVar(value=self.config_data.get(stat_name, True))
            self.vars[stat_name] = var
            
            switch = ctk.CTkSwitch(
                card, text="", variable=var,
                command=lambda s=stat_name: self.toggle_hack(s),
                progress_color=self.accent_color, button_color="#ffffff", button_hover_color="#dddddd"
            )
            # Position switch to the right
            switch.place(relx=1.0, rely=0.5, anchor="e", x=-15)
            switch.configure(state="disabled")
            self.vars[stat_name].chk = switch

            col_idx += 1
            if col_idx > 1:
                col_idx = 0
                row_idx += 1

        # Sliders Frame
        self.sliders_frame = ctk.CTkFrame(self.main_frame, fg_color=self.card_bg, corner_radius=10)
        self.sliders_frame.grid(row=2, column=0, sticky="ew")
        self.sliders_frame.grid_columnconfigure(0, weight=1)

        # Move Speed Slider
        self.lbl_move = ctk.CTkLabel(self.sliders_frame, text=f"Movement Speed: {self.config_data.get('move_slider', 250)}", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_move.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="w")
        
        self.move_slider = ctk.CTkSlider(
            self.sliders_frame, from_=50, to=3000, number_of_steps=59,
            button_color=self.accent_color, button_hover_color=self.accent_hover, progress_color=self.accent_color,
            command=self.update_move_slider
        )
        self.move_slider.set(self.config_data.get("move_slider", 250))
        self.move_slider.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="ew")
        
        # Attack Speed Slider
        self.lbl_atk = ctk.CTkLabel(self.sliders_frame, text=f"Attack Speed: {self.config_data.get('atk_slider', 2000)}", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_atk.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.atk_slider = ctk.CTkSlider(
            self.sliders_frame, from_=1000, to=85000, number_of_steps=84,
            button_color=self.accent_color, button_hover_color=self.accent_hover, progress_color=self.accent_color,
            command=self.update_atk_slider
        )
        self.atk_slider.set(self.config_data.get("atk_slider", 2000))
        self.atk_slider.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")

        # Footer
        footer = ctk.CTkLabel(self.main_frame, text="* Dica: Se a fase resetar constantemente, diminua o MoveSpeed.", font=ctk.CTkFont(size=12), text_color=self.accent_hover)
        footer.grid(row=3, column=0, pady=(20, 0), sticky="w")

    def add_log(self, text, clear=False):
        self.instances_box.configure(state="normal")
        if clear:
            self.instances_box.delete("0.0", "end")
        self.instances_box.insert("end", text + "\n")
        self.instances_box.see("end")
        self.instances_box.configure(state="disabled")
        self.update()

    def update_move_slider(self, value):
        self.lbl_move.configure(text=f"Movement Speed: {int(value)}")
        self.save_config()

    def update_atk_slider(self, value):
        self.lbl_atk.configure(text=f"Attack Speed: {int(value)}")
        self.save_config()

    def load_config(self):
        default_config = {
            "Max HP": True,
            "Attack Damage": True,
            "Attack Speed": True,
            "Move Speed": True,
            "move_slider": 250,
            "atk_slider": 2000
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception:
                pass
        return default_config

    def save_config(self, *args):
        if not hasattr(self, 'vars') or 'Max HP' not in self.vars:
            return
        config = {
            "Max HP": self.vars["Max HP"].get(),
            "Attack Damage": self.vars["Attack Damage"].get(),
            "Attack Speed": self.vars["Attack Speed"].get(),
            "Move Speed": self.vars["Move Speed"].get(),
            "move_slider": self.move_slider.get(),
            "atk_slider": self.atk_slider.get()
        }
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass

    def do_connect(self):
        pids = find_all_processes()
        if not pids:
            messagebox.showerror("Erro", f"Nenhum processo '{PROCESS_NAME}' encontrado!\n\nCertifique-se de que o jogo esta rodando em todas as instancias.")
            return
        
        self.lbl_status.configure(text=f"{len(pids)} instâncias encontradas...", text_color="#ffff00")
        self.add_log("", clear=True)
        self.update()
        
        self.engines = []
        
        for pid in pids:
            engine = TbhHackEngine(pid)
            ok, msg = engine.connect()
            self.add_log(msg)
            
            if not ok: continue
            
            ok, msg = engine.scan_aob()
            self.add_log(f"  ↳ {msg}")
            
            if not ok: continue
            self.engines.append(engine)
        
        connected_count = len(self.engines)
        
        if connected_count == 0:
            self.lbl_status.configure(text="FALHA na injeção.", text_color="#ff3333")
            return
        
        # Ativar interface
        self.lbl_status.configure(text=f"CONECTADO ({connected_count}/{len(pids)})", text_color="#00ffcc")
        self.btn_connect.configure(state="disabled", text="INJETADO", fg_color="#2e7d32", hover_color="#2e7d32")
        self.btn_rescan.configure(state="normal")
        
        for var in self.vars.values():
            var.chk.configure(state="normal")
        
        # Iniciar hack loops para todas as instancias
        for engine in self.engines:
            threading.Thread(
                target=engine.hack_loop,
                args=(lambda: (self.atk_slider.get(), self.move_slider.get()),),
                daemon=True
            ).start()

    def toggle_hack(self, stat_name):
        new_state = self.vars[stat_name].get()
        for engine in self.engines:
            engine.active_hacks[stat_name] = new_state
        self.save_config()

    def rescan_instances(self):
        # Para engines antigas
        for engine in self.engines:
            engine.running = False
        self.engines = []
        
        self.btn_connect.configure(state="normal", text="INJETAR", fg_color=self.accent_color, hover_color=self.accent_hover)
        for var in self.vars.values():
            var.chk.configure(state="disabled")
        self.btn_rescan.configure(state="disabled")
        self.lbl_status.configure(text="Aguardando reconexão...", text_color=self.sub_text)
        self.add_log("Desconectado. Aguardando nova injeção...", clear=True)

if __name__ == "__main__":
    app = HackApp()
    app.mainloop()
