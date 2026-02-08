import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import re
import chardet
import os
import threading
from tkinter import scrolledtext

# ---------- 유틸리티 (인코딩 감지 및 공백 치환) ----------

def read_text_with_autodetect(file_path):
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        detected = chardet.detect(raw)
        enc_candidate = detected["encoding"]
        for e in ["gb18030", enc_candidate, "utf-8", "cp949"]:
            if not e: continue
            try:
                content = raw.decode(e, errors="strict")
                return content, e
            except (UnicodeDecodeError, LookupError):
                continue
        final_enc = enc_candidate if enc_candidate else "utf-8"
        content = raw.decode(final_enc, errors="replace")
        return content, final_enc
    except Exception as e:
        return f"파일 읽기 오류: {str(e)}", "utf-8"

# ---------- 메인 앱 클래스 ----------
class TextToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Tool (Auto Path & Input Fix)")
        self.root.geometry("500x750")

        self.save_path = tk.StringVar(value=os.getcwd())

        # 탭 설정
        self.notebook = ttk.Notebook(self.root, width=480, height=450)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=5)
        
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("맑은 고딕", 14))

        self.setup_merge_tab()
        self.setup_split_tab()
        self.setup_editor_tab()

        # 하단 공통 영역
        common_frame = ttk.LabelFrame(self.root, text=" 설정 및 진행 상태 ")
        common_frame.pack(fill="x", padx=15, pady=5)

        path_box = ttk.Frame(common_frame)
        path_box.pack(fill="x", padx=5, pady=5)
        
        top_row = ttk.Frame(path_box)
        top_row.pack(fill="x", pady=2)
        ttk.Label(top_row, text="저장 위치:").pack(side="left")
        self.path_entry = ttk.Entry(top_row, textvariable=self.save_path)
        self.path_entry.pack(side="left", expand=True, fill="x", padx=5)
        self.path_entry.bind("<Button-1>", lambda e: self.path_entry.focus_set()) # 키보드 픽스

        btn_row = ttk.Frame(path_box)
        btn_row.pack(fill="x", pady=5)
        ttk.Button(btn_row, text="저장 경로 변경", command=self.select_save_path).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row, text="새 폴더 생성", command=self.create_new_folder).pack(side="left", expand=True, fill="x", padx=2)

        self.status_label = ttk.Label(common_frame, text="준비 완료: 0%", font=("Arial", 10, "bold"))
        self.status_label.pack(pady=5)
        self.progress = ttk.Progressbar(common_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5, padx=10, fill="x")

    def create_new_folder(self):
        base_path = self.save_path.get()
        if not base_path or not os.path.exists(base_path):
            messagebox.showwarning("주의", "먼저 유효한 상위 저장 위치를 선택해 주세요.")
            return
        new_name = simpledialog.askstring("새 폴더 생성", "생성할 폴더 이름을 입력하세요:", parent=self.root)
        if new_name:
            full_path = os.path.join(base_path, new_name.strip())
            try:
                if not os.path.exists(full_path):
                    os.makedirs(full_path)
                    self.save_path.set(full_path)
                    messagebox.showinfo("완료", f"새 폴더가 생성되었습니다:\n{new_name}")
                else:
                    messagebox.showwarning("중복", "이미 존재하는 폴더 이름입니다.")
            except Exception as e:
                messagebox.showerror("오류", f"폴더 생성에 실패했습니다:\n{e}")

    def select_save_path(self):
        path = filedialog.askdirectory()
        if path:
            self.save_path.set(path)

    def update_auto_path(self, file_path):
        if file_path:
            self.save_path.set(os.path.dirname(file_path))

    def update_status(self, current, total):
        percent = int((current / total) * 100) if total > 0 else 0
        self.progress["value"] = percent
        self.status_label.config(text=f"진행 중: {percent}% ({current}/{total})")
        self.root.update_idletasks()
        
    def final_clean_for_save(self, text):
        if not text: return ""
        text = text.replace('\ufffd', ' ')
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ', text)
        text = re.sub(r'[\uE000-\uF8FF\uD800-\uDFFF]', ' ', text)
        bad_ws = ['\u3000', '\ufeff', '\xa0', '\u200b', '\u200c', '\u200d']
        for ws in bad_ws:
            text = text.replace(ws, ' ')
        return text

    # ---------- 텍스트 편집 탭 ----------
    def setup_editor_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" 텍스트 편집 ")
        tk.Label(frame, text="", height=1).pack()
        self.editor_file_path = None
        self.editor_encoding = "utf-8"

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="파일 열기", command=self.editor_open_file).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="저장", command=self.editor_save_file).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="다른 이름으로 저장", command=self.editor_save_as).pack(side="left", padx=5)

        self.editor_text = scrolledtext.ScrolledText(frame, wrap="word", font=("맑은 고딕", 12))
        self.editor_text.pack(expand=True, fill="both", padx=10, pady=10)
        self.editor_text.bind("<Button-1>", lambda e: self.editor_text.focus_set()) # 키보드 픽스

    def editor_open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            content, enc = read_text_with_autodetect(file_path)
            self.editor_encoding = enc
            self.editor_text.delete(1.0, tk.END)
            self.editor_text.insert(tk.END, content)
            self.editor_file_path = file_path
            self.update_auto_path(file_path)
            self.root.title(f"Text Tool - {file_path} ({enc})")

    def editor_save_file(self):
        if self.editor_file_path:
            try:
                content = self.editor_text.get(1.0, tk.END)
                clean_content = self.final_clean_for_save(content)
                with open(self.editor_file_path, "w", encoding=self.editor_encoding, errors="replace") as f:
                    f.write(clean_content)
                messagebox.showinfo("저장 완료", f"깨진 기호를 정제하여 {self.editor_encoding}으로 저장했습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"파일을 저장할 수 없습니다: {e}")
        else:
            messagebox.showwarning("경고", "먼저 파일을 열어주세요.")

    def editor_save_as(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                content = self.editor_text.get(1.0, tk.END)
                clean_content = self.final_clean_for_save(content)
                with open(file_path, "w", encoding=self.editor_encoding, errors="replace") as f:
                    f.write(clean_content)
                messagebox.showinfo("저장 완료", f"정제 후 새 파일로 저장되었습니다.")
                self.editor_file_path = file_path
                self.root.title(f"Text Tool - {file_path} ({self.editor_encoding})")
            except Exception as e:
                messagebox.showerror("오류", f"파일을 저장할 수 없습니다: {e}")

    # ---------- 병합 탭 ----------
    def setup_merge_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="    병  합    ")
        tk.Label(frame, text="", height=1).pack() 

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="    파일 선택    ", command=self.select_merge_files, height=2).pack(side="left", padx=5)
        tk.Button(btn_frame, text="폴더 불러오기", command=self.select_merge_folder, height=2).pack(side="left", padx=5)
        tk.Button(btn_frame, text="    선택 삭제    ", command=self.delete_selected_file, height=2).pack(side="left", padx=5)
        
        self.merge_files = []
        self.merge_listbox = tk.Listbox(frame, height=25, selectmode="multiple")
        self.merge_listbox.pack(fill="x", padx=10)
        
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(input_frame, text="묶음:").pack(side="left")
        self.group_size_entry = ttk.Entry(input_frame, width=5)
        self.group_size_entry.insert(0, "5")
        self.group_size_entry.pack(side="left", padx=5, ipady=5)
        self.group_size_entry.bind("<Button-1>", lambda e: self.group_size_entry.focus_set()) # 키보드 픽스
        
        ttk.Label(input_frame, text="저장 파일명:").pack(side="left", padx=(10, 0))
        self.merge_output_entry = ttk.Entry(input_frame, width=25)
        self.merge_output_entry.pack(side="left", padx=5, ipady=5)
        self.merge_output_entry.bind("<Button-1>", lambda e: self.merge_output_entry.focus_set()) # 키보드 픽스
        
        tk.Button(frame, text="병합 시작", command=lambda: threading.Thread(target=self.run_merge_thread).start(), height=2, width=15).pack(pady=10)

    def select_merge_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Text files", "*.txt")])
        if files:
            self.update_auto_path(files[0])
            if not self.merge_files:
                name = os.path.splitext(os.path.basename(files[0]))[0]
                clean_name = re.sub(r'_\d{7,}$', '', name)
                self.merge_output_entry.delete(0, tk.END)
                self.merge_output_entry.insert(0, f"{clean_name}_M")
            for f in files:
                if f not in self.merge_files:
                    self.merge_files.append(f)
                    self.merge_listbox.insert(tk.END, os.path.basename(f))

    def select_merge_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path.set(folder)
            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".txt")]
            files.sort()
            if files and not self.merge_files:
                name = os.path.splitext(os.path.basename(files[0]))[0]
                clean_name = re.sub(r'_\d{7,}$', '', name)
                self.merge_output_entry.delete(0, tk.END)
                self.merge_output_entry.insert(0, f"{clean_name}_M")
            for f in files:
                if f not in self.merge_files:
                    self.merge_files.append(f)
                    self.merge_listbox.insert(tk.END, os.path.basename(f))

    def delete_selected_file(self):
        selection = self.merge_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 파일을 선택하세요.")
            return
        for index in reversed(selection):
            self.merge_listbox.delete(index)
            del self.merge_files[index]

    def run_merge_thread(self):
        if not self.merge_files: 
            messagebox.showwarning("경고", "병합할 파일을 선택해주세요.")
            return
        output_base = self.merge_output_entry.get().strip()
        save_dir = self.save_path.get()
        try:
            group_size = int(self.group_size_entry.get().strip())
        except ValueError:
            messagebox.showerror("오류", "묶음 크기에 숫자를 입력해주세요.")
            return
        total_files = len(self.merge_files)
        file_groups = [self.merge_files[i : i + group_size] for i in range(0, total_files, group_size)]
        try:
            _, first_enc = read_text_with_autodetect(self.merge_files[0])
            processed_count = 0
            for group in file_groups:
                def get_file_num(path):
                    match = re.search(r'(\d+)\.txt$', path)
                    return f"{int(match.group(1)):04d}" if match else "0000"
                start_num = get_file_num(group[0])
                end_num = get_file_num(group[-1])
                output_filename = f"{output_base}_{start_num}-{end_num}.txt"
                with open(os.path.join(save_dir, output_filename), "w", encoding=first_enc, errors="replace") as out:
                    for f_path in group:
                        content, _ = read_text_with_autodetect(f_path)
                        out.write(self.final_clean_for_save(content) + "\n")
                        processed_count += 1
                        self.update_status(processed_count, total_files)
            messagebox.showinfo("완료", "범위 지정 병합이 완료되었습니다.")
        except Exception as e: 
            messagebox.showerror("오류", f"병합 중 오류 발생: {str(e)}")
        finally:
            self.status_label.config(text="병합 처리 완료")

    # ---------- 분할 탭 ----------
    def setup_split_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="    분  할    ")
        tk.Label(frame, text="", height=1).pack() 
        tk.Button(frame, text="파일 선택", command=self.select_split_file, height=2, width=15).pack(pady=5)
        self.split_file = ""
        self.split_listbox = tk.Listbox(frame, height=3) # 높이 3 복구
        self.split_listbox.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame, text="기준값:").pack()
        self.split_input_entry = ttk.Entry(frame)
        self.split_input_entry.insert(0, r"\b第\d+章\b")
        self.split_input_entry.pack(fill="x", padx=10, ipady=10)
        self.split_input_entry.bind("<Button-1>", lambda e: self.split_input_entry.focus_set()) # 키보드 픽스
        
        m_frame = ttk.Frame(frame)
        m_frame.pack(pady=5)
        self.split_mode = tk.StringVar(value="regex")
        ttk.Radiobutton(m_frame, text="정규식", variable=self.split_mode, value="regex").pack(side="left")
        ttk.Radiobutton(m_frame, text="글자수", variable=self.split_mode, value="chars").pack(side="left")
        ttk.Radiobutton(m_frame, text="라인수", variable=self.split_mode, value="lines").pack(side="left")
        
        ttk.Label(frame, text="저장 파일명:").pack()
        self.split_output_entry = ttk.Entry(frame)
        self.split_output_entry.pack(fill="x", padx=10, ipady=10)
        self.split_output_entry.bind("<Button-1>", lambda e: self.split_output_entry.focus_set()) # 키보드 픽스
        
        tk.Button(frame, text="분할 시작", command=lambda: threading.Thread(target=self.run_split_thread).start(), height=2, width=15).pack(pady=10)

    def select_split_file(self):
        file = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file:
            self.split_file = file
            self.split_listbox.delete(0, tk.END)
            self.split_listbox.insert(tk.END, os.path.basename(file))
            self.update_auto_path(file)
            name = os.path.splitext(os.path.basename(file))[0]
            clean_name = re.sub(r'_\d{7,}$', '', name)
            self.split_output_entry.delete(0, tk.END)
            self.split_output_entry.insert(0, f"{clean_name}_S")

    def run_split_thread(self):
        if not self.split_file: return
        base = self.split_output_entry.get().strip()
        val = self.split_input_entry.get().strip()
        mode, save_dir = self.split_mode.get(), self.save_path.get()
        try:
            text, enc = read_text_with_autodetect(self.split_file)
            text = self.final_clean_for_save(text)
            if mode == "regex":
                parts = re.split(f"({val})", text)
                chunks, current = [], ""
                for p in parts:
                    if re.match(val, p):
                        if current: chunks.append(current)
                        current = p
                    else: current += p
                if current: chunks.append(current)
            elif mode == "chars":
                size = int(val)
                chunks = [text[i:i+size] for i in range(0, len(text), size)]
            else: # lines
                size = int(val)
                lines = text.splitlines(keepends=True)
                chunks = ["".join(lines[i:i+size]) for i in range(0, len(lines), size)]
            total = len(chunks)
            for i, c in enumerate(chunks, 1):
                filename = f"{base}_{i:07d}.txt"
                with open(os.path.join(save_dir, filename), "w", encoding=enc, errors="replace") as f:
                    f.write(c)
                self.update_status(i, total)
            messagebox.showinfo("완료", f"총 {total}개의 파일로 분할 완료되었습니다.")
        except Exception as e: 
            messagebox.showerror("오류", f"분할 중 오류 발생: {str(e)}")
        finally: 
            self.status_label.config(text="분할 처리 종료")

if __name__ == "__main__":
    root = tk.Tk()
    app = TextToolApp(root)
    root.mainloop()
