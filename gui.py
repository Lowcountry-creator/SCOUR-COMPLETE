"""Development GUI shell. No independently verified design results."""
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from dataclasses import asdict
from legacy.hy8_io import inputs_from_hy8
from pathlib import Path
from tempfile import TemporaryDirectory
from scour_complete import run_case, run_batch, STATUS, INFERENCES

def import_draft(path, crossing, culvert, flow, *, confirmed=False):
    inputs = inputs_from_hy8(path, crossing, culvert, flow, confirm_tailwater_datum=confirmed)
    draft = asdict(inputs)
    # Re-enter material, lining and energy dissipation data for this event.
    for field in ("V_LB", "D50_trial", "min_class", "Ss", "V_perm", "tau_perm"):
        draft[field] = None
    return draft


def display_report(result):
    cases = result if isinstance(result, list) else [result]
    return "\n\n".join(case.get("report") or f"Case {case['index'] + 1}: {case['error']}"
                       for case in cases)


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
    controls = ttk.Frame(inputs)
    controls.pack(side="bottom", fill="x")
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
    def load_hy8():
        path = filedialog.askopenfilename(filetypes=[("HY-8 project", "*.hy8")])
        if not path:
            return
        selectors = []
        for label in ("Crossing index", "Culvert index", "Flow column index"):
            value = simpledialog.askinteger("HY-8 selection", label + " (zero-based)", minvalue=0)
            if value is None:
                return
            selectors.append(value)
        try:
            try:
                draft = import_draft(path, *selectors)
            except ValueError as exc:
                if "Confirm the common elevation datum" not in str(exc):
                    raise
                if not messagebox.askyesno("Tailwater datum", str(exc)):
                    return
                draft = import_draft(path, *selectors, confirmed=True)
        except (ValueError, OSError, KeyError, IndexError) as exc:
            messagebox.showerror("HY-8 import", str(exc))
            return
        state["result"] = None
        source.delete("1.0", "end")
        source.insert("1.0", json.dumps(draft, indent=2))
        messagebox.showinfo("Imported event", "Replace null material and hydraulic criteria before running.")

    def run():
        state["result"] = None
        output.delete("1.0", "end")
        try:
            data = json.loads(source.get("1.0", "end"))
            state["result"] = run_batch(data) if isinstance(data, list) else run_case(data)
            output.delete("1.0", "end")
            output.insert("1.0", display_report(state["result"]))
            tabs.select(results)
        except Exception as exc:
            messagebox.showerror("Input or calculation error", str(exc))
    def export():
        if state["result"] is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path:
            Path(path).write_text(json.dumps(state["result"], indent=2, allow_nan=False), encoding="utf-8")
    def show_plot():
        cases = state["result"]
        if cases is None:
            return
        case = cases
        if isinstance(cases, list):
            if not cases:
                return
            number = simpledialog.askinteger("Velocity plot", "Case number (starting at 1)",
                                             minvalue=1, maxvalue=len(cases))
            if number is None:
                return
            case = cases[number - 1]
        if "error" in case:
            messagebox.showerror("Case error", case["error"])
            return
        from visuals import export_velocity_plot
        with TemporaryDirectory() as folder:
            path = Path(folder) / "velocity.png"
            export_velocity_plot(case, path)
            photo = tk.PhotoImage(file=path).subsample(2)
        window = tk.Toplevel(root)
        window.title("Velocity profile")
        chart = ttk.Label(window, image=photo)
        chart.image = photo
        chart.pack()

    def export_reports():
        if state["result"] is None:
            return
        folder = filedialog.askdirectory()
        if folder:
            from reporting import export_batch
            cases = state["result"]
            summary = export_batch(cases if isinstance(cases, list) else [cases], folder)
            failures = [r["error"] for r in summary if r["error"]]
            if failures:
                messagebox.showerror("Report export", "\n".join(failures))

    for label, callback in [("Load JSON", load), ("Import HY-8", load_hy8), ("Run legacy screening", run), ("Export JSON", export),
                            ("Velocity plot", show_plot), ("Export PDF, text and chart", export_reports)]:
        ttk.Button(controls, text=label, command=callback).pack(side="left", padx=5, pady=5)
    root.mainloop()

if __name__ == "__main__":
    main()
