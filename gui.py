"""Development GUI shell. No independently verified design results."""
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from scour_complete import run_case, run_batch, STATUS, INFERENCES

def main():
    root = tk.Tk()
    root.title("SCOUR-COMPLETE | Development")
    root.geometry("1000x700")
    ttk.Label(root, text=STATUS).pack(pady=8)
    tabs = ttk.Notebook(root)
    tabs.pack(fill="both", expand=True)
    inputs = ttk.Frame(tabs)
    results = ttk.Frame(tabs)
    qc = ttk.Frame(tabs)
    tabs.add(inputs, text="Input / Batch")
    tabs.add(results, text="Legacy calculations")
    tabs.add(qc, text="QC / Inferences")
    source = tk.Text(inputs, wrap="none")
    source.pack(fill="both", expand=True)
    output = tk.Text(results, wrap="word")
    output.pack(fill="both", expand=True)
    ttk.Label(qc, text="\n\n".join(INFERENCES), wraplength=900).pack(padx=20, pady=20)
    state = {"result": None}
    def load():
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            source.delete("1.0", "end")
            source.insert("1.0", Path(path).read_text(encoding="utf-8"))
    def run():
        try:
            data = json.loads(source.get("1.0", "end"))
            state["result"] = run_batch(data) if isinstance(data, list) else run_case(data)
            output.delete("1.0", "end")
            output.insert("1.0", json.dumps(state["result"], indent=2))
            tabs.select(results)
        except Exception as exc:
            messagebox.showerror("Input or calculation error", str(exc))
    def export():
        if state["result"] is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path:
            Path(path).write_text(json.dumps(state["result"], indent=2, allow_nan=False), encoding="utf-8")
    for label, callback in [("Load JSON", load), ("Run legacy screening", run), ("Export JSON", export)]:
        ttk.Button(inputs, text=label, command=callback).pack(side="left", padx=5, pady=5)
    root.mainloop()

if __name__ == "__main__":
    main()
