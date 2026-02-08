import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import chardet
import os
import threading
from tkinter import scrolledtext

# ---------- 유틸리티 (인코딩 감지 및 공백 치환) ----------

def read_text_with_autodetect(file_path):
    """
    파일의 인코딩을 감지하고 텍스트를 읽어옵니다.
    불러올 때는 필터링을 하지 않고, 인코딩 오류 시 블랙 다이어몬드(\ufffd)를 생성합니다.
    """
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        
        # 1. chardet으로 인코딩 감지
        detected = chardet.detect(raw)
        enc_candidate = detected["encoding"]
        
        # 2. 인코딩 시도 순서: 중국어 표준(gb18030) -> 감지된 결과 -> 유니코드(utf-8) -> 한국어(cp949)
        # gb18030은 gb2312와 gbk를 모두 포함하므로 가장 먼저 시도하는 것이 안전합니다.
        for e in ["gb18030", enc_candidate, "utf-8", "cp949"]:
            if not e: continue
            try:
                # errors="strict"로 시도하여 완벽하게 일치하는 인코딩을 찾습니다.
                content = raw.decode(e, errors="strict")
                return content, e
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 3. 모든 시도가 완벽하지 않을 경우: 
        # 가장 가능성 높은 인코딩으로 읽되, 깨진 바이트는 블랙 다이어몬드(\ufffd)로 표시합니다.
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
        self.root.geometry("500x650")

        # 저장 경로 변수
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
        
        # 1층: "저장 위치" 라벨과 주소창을 한 줄에
        top_row = ttk.Frame(path_box)
        top_row.pack(fill="x", pady=2)
        ttk.Label(top_row, text="저장 위치:").pack(side="left")
        self.path_entry = ttk.Entry(top_row, textvariable=self.save_path)
        self.path_entry.pack(side="left", expand=True, fill="x", padx=5)

        # 2층: 변경 및 새 폴더 버튼을 아래 줄에 배치 (가로로 균등하게)
        btn_row = ttk.Frame(path_box)
        btn_row.pack(fill="x", pady=5)
        
        # 버튼 사이의 간격을 벌리고 가로 길이를 충분히 확보
        ttk.Button(btn_row, text="저장 경로 변경", command=self.select_save_path).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row, text="새 폴더 생성", command=self.create_new_folder).pack(side="left", expand=True, fill="x", padx=2)

        # 상태 및 프로그레스바 (기존 동일)
        self.status_label = ttk.Label(common_frame, text="준비 완료: 0%", font=("Arial", 10, "bold"))
        self.status_label.pack(pady=5)
        self.progress = ttk.Progressbar(common_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5, padx=10, fill="x")

    def create_new_folder(self):
        """현재 설정된 저장 위치 하위에 새로운 폴더를 생성합니다."""
        from tkinter import simpledialog
        
        # 1. 현재 저장 위치 가져오기
        base_path = self.save_path.get()
        if not base_path or not os.path.exists(base_path):
            messagebox.showwarning("주의", "먼저 유효한 상위 저장 위치를 선택해 주세요.")
            return

        # 2. 사용자에게 새 폴더 이름 입력받기
        new_name = simpledialog.askstring("새 폴더 생성", "생성할 폴더 이름을 입력하세요:", parent=self.root)
        
        if new_name:
            # 공백 제어 및 경로 병합
            new_name = new_name.strip()
            full_path = os.path.join(base_path, new_name)
            
            try:
                if not os.path.exists(full_path):
                    os.makedirs(full_path)
                    # 3. 생성된 새 폴더로 저장 경로 자동 업데이트
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
        """파일 경로에서 디렉토리를 추출하여 저장 경로를 자동 업데이트합니다."""
        if file_path:
            folder_path = os.path.dirname(file_path)
            self.save_path.set(folder_path)

    def update_status(self, current, total):
        percent = int((current / total) * 100) if total > 0 else 0
        self.progress["value"] = percent
        self.status_label.config(text=f"진행 중: {percent}% ({current}/{total})")
        self.root.update_idletasks()
        
    def final_clean_for_save(self, text):
        """저장/처리 직전에 호출하며, 줄바꿈은 보존하고 깨진 기호만 정제합니다."""
        if not text: return ""
        
        # 1. 블랙 다이아몬드(\ufffd) 기호를 일반 공백으로
        text = text.replace('\ufffd', ' ')
        
        # 2. 보이지 않는 제어 문자 제거 (줄바꿈 \n, \r 및 탭 \t은 제외)
        # \x00-\x08, \x0b, \x0c, \x0e-\x1f 등을 타겟팅합니다.
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ', text)
        
        # 3. 이상한 한자의 주범(PUA 영역 등) 제거
        # [\uE000-\uF8FF] 영역 등을 공백으로 치환
        text = re.sub(r'[\uE000-\uF8FF\uD800-\uDFFF]', ' ', text)
        
        # 4. 중국어 전각 공백 및 기타 유령 공백들 정리
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

        # 버튼 영역
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="파일 열기", command=self.editor_open_file).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="저장", command=self.editor_save_file).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="다른 이름으로 저장", command=self.editor_save_as).pack(side="left", padx=5)

        # 텍스트 영역
        self.editor_text = scrolledtext.ScrolledText(frame, wrap="word", font=("맑은 고딕", 12))
        self.editor_text.pack(expand=True, fill="both", padx=10, pady=10)

    def editor_open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            # 유틸리티의 함수를 사용하여 필터링 없이 그대로 읽어옴 (다이아몬드 노출됨)
            content, enc = read_text_with_autodetect(file_path)
            
            self.editor_encoding = enc
            self.editor_text.delete(1.0, tk.END)
            self.editor_text.insert(tk.END, content)
            self.editor_file_path = file_path
            self.update_auto_path(file_path)
            self.root.title(f"Text Tool - {file_path} ({enc})")

    def editor_save_file(self):
        """현재 열린 파일에 정제된 내용을 덮어씁니다."""
        if self.editor_file_path:
            try:
                # 1. 편집기 화면의 텍스트 가져오기
                content = self.editor_text.get(1.0, tk.END)
                
                # 2. 공통 함수를 사용하여 깨진 문자 세척
                clean_content = self.final_clean_for_save(content)
                
                # 3. 파일 저장
                with open(self.editor_file_path, "w", encoding=self.editor_encoding, errors="replace") as f:
                    f.write(clean_content)
                
                messagebox.showinfo("저장 완료", f"깨진 기호를 정제하여 {self.editor_encoding}으로 저장했습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"파일을 저장할 수 없습니다: {e}")
        else:
            messagebox.showwarning("경고", "먼저 파일을 열어주세요.")

    def editor_save_as(self):
        """정제된 내용을 새로운 파일로 저장합니다."""
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                # 1. 편집기 화면의 텍스트 가져오기
                content = self.editor_text.get(1.0, tk.END)
                
                # 2. 공통 함수를 사용하여 깨진 문자 세척
                clean_content = self.final_clean_for_save(content)
                
                # 3. 새로운 경로에 저장
                with open(file_path, "w", encoding=self.editor_encoding, errors="replace") as f:
                    f.write(clean_content)
                
                messagebox.showinfo("저장 완료", f"정제 후 새 파일로 저장되었습니다.")
                self.editor_file_path = file_path # 현재 경로 업데이트
                self.root.title(f"Text Tool - {file_path} ({self.editor_encoding})")
            except Exception as e:
                messagebox.showerror("오류", f"파일을 저장할 수 없습니다: {e}")

    # ---------- 병합 탭 UI ----------
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
        
        # 묶음 크기와 파일명을 입력받는 프레임
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        # 묶음 크기 추가
        ttk.Label(input_frame, text="묶음:").pack(side="left")
        self.group_size_entry = ttk.Entry(input_frame, width=5)
        self.group_size_entry.insert(0, "5") # 기본값 5개씩 묶기
        self.group_size_entry.pack(side="left", padx=5, ipady=5)
        
        ttk.Label(input_frame, text="저장 파일명:").pack(side="left", padx=(10, 0))
        self.merge_output_entry = ttk.Entry(input_frame, width=25)
        # self.merge_output_entry.insert(0, "merged_result")
        self.merge_output_entry.pack(side="left", padx=5, ipady=5)
        
        tk.Button(frame, text="병합 시작", 
                  command=lambda: threading.Thread(target=self.run_merge_thread).start(), 
                  height=2, width=15).pack(pady=10)

    def select_merge_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Text files", "*.txt")])
        if files:
            self.update_auto_path(files[0])
            
            # [핵심 로직] 리스트가 비어있을 때(첫 파일 불러올 때)만 이름 자동 설정
            if not self.merge_files:
                # 1. 첫 번째 파일명에서 확장자 제거
                name = os.path.splitext(os.path.basename(files[0]))[0]
                
                # 2. 파일명 끝의 '_7자리이상숫자' 제거
                clean_name = re.sub(r'_\d{7,}$', '', name)
                
                # 3. 뒤에 _M 붙이기
                suggested_name = f"{clean_name}_M"
                
                # 4. 파일명 입력창(self.merge_output_entry) 업데이트
                self.merge_output_entry.delete(0, tk.END)
                self.merge_output_entry.insert(0, suggested_name)
            
            for f in files:
                if f not in self.merge_files:
                    self.merge_files.append(f)
                    self.merge_listbox.insert(tk.END, os.path.basename(f))

    def select_merge_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path.set(folder) # 폴더 선택 시 해당 폴더를 저장 위치로 설정
            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".txt")]
            files.sort() # 이름순 정렬
            
            # [파일명 자동 업데이트 로직]
            # 리스트에 파일이 하나도 없을 때만 첫 번째 파일명을 기준으로 이름 생성
            if files and not self.merge_files:
                # 1. 첫 번째 파일명에서 확장자 제거
                name = os.path.splitext(os.path.basename(files[0]))[0]
                
                # 2. 파일명 끝의 '_7자리이상숫자' 제거
                clean_name = re.sub(r'_\d{7,}$', '', name)
                
                # 3. 뒤에 _M 붙여서 입력창에 세팅
                suggested_name = f"{clean_name}_M"
                self.merge_output_entry.delete(0, tk.END)
                self.merge_output_entry.insert(0, suggested_name)

            # 리스트박스 및 내부 변수에 파일 추가
            for f in files:
                if f not in self.merge_files:
                    self.merge_files.append(f)
                    self.merge_listbox.insert(tk.END, os.path.basename(f))

    def delete_selected_file(self):
        selection = self.merge_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 파일을 선택하세요.")
            return
        # 인덱스가 변하지 않도록 뒤에서부터 삭제
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
                # --- [번지수 추출 로직 시작] ---
                def get_file_num(path):
                    """파일명 끝의 숫자를 찾아 4자리 문자열로 반환 (없으면 '0000')"""
                    match = re.search(r'(\d+)\.txt$', path)
                    if match:
                        # 숫자가 너무 길면 뒤의 4자리만, 짧으면 0을 채움
                        return f"{int(match.group(1)):04d}"
                    return "0000"

                start_num = get_file_num(group[0])
                end_num = get_file_num(group[-1])
                
                # 테스트_M_0001-0005 형태의 파일명 생성
                output_filename = f"{output_base}_{start_num}-{end_num}.txt"
                output_path = os.path.join(save_dir, output_filename)
                # --- [번지수 추출 로직 끝] ---
                
                with open(output_path, "w", encoding=first_enc, errors="replace") as out:
                    for f_path in group:
                        content, _ = read_text_with_autodetect(f_path)
                        clean_content = self.final_clean_for_save(content)
                        out.write(clean_content + "\n")
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
        self.split_listbox = tk.Listbox(frame, height=3)
        self.split_listbox.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame, text="기준값:").pack()
        self.split_input_entry = ttk.Entry(frame)
        self.split_input_entry.insert(0, r"\b第\d+章\b")
        self.split_input_entry.pack(fill="x", padx=10, ipady=10) # ipady로 입력 영역 확장
        
        m_frame = ttk.Frame(frame)
        m_frame.pack(pady=5)
        self.split_mode = tk.StringVar(value="regex")
        ttk.Radiobutton(m_frame, text="정규식", variable=self.split_mode, value="regex").pack(side="left")
        ttk.Radiobutton(m_frame, text="글자수", variable=self.split_mode, value="chars").pack(side="left")
        ttk.Radiobutton(m_frame, text="라인수", variable=self.split_mode, value="lines").pack(side="left")
        
        ttk.Label(frame, text="저장 파일명:").pack()
        self.split_output_entry = ttk.Entry(frame)
        # self.split_output_entry.insert(0, "split_result")
        self.split_output_entry.pack(fill="x", padx=10, ipady=10)
        
        tk.Button(frame, text="분할 시작", command=lambda: threading.Thread(target=self.run_split_thread).start(), height=2, width=15).pack(pady=10)

    def select_split_file(self):
        file = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file:
            self.split_file = file
            self.split_listbox.delete(0, tk.END)
            self.split_listbox.insert(tk.END, os.path.basename(file))
            self.update_auto_path(file)

            # [핵심 로직]
            # 1. 원본 파일명에서 확장자 제거 (예: '테스트_0000001')
            name = os.path.splitext(os.path.basename(file))[0]
            
            # 2. 파일명 끝의 '_7자리이상숫자'만 제거 (예: '테스트_0000001' -> '테스트')
            clean_name = re.sub(r'_\d{7,}$', '', name)
            
            # 3. 뒤에 _S 붙이기
            suggested_name = f"{clean_name}_S"
            
            # 4. 출력 파일명 입력창(self.split_output_entry) 업데이트
            self.split_output_entry.delete(0, tk.END)
            self.split_output_entry.insert(0, suggested_name)

    def run_split_thread(self):
        if not self.split_file: return
        base = self.split_output_entry.get().strip()
        val = self.split_input_entry.get().strip()
        mode = self.split_mode.get()
        save_dir = self.save_path.get()
        
        try:
            # 1. 파일 읽기 (원본 그대로)
            text, enc = read_text_with_autodetect(self.split_file)
            
            # 2. 분할 작업 전 공통 세척 함수로 '블랙 다이아몬드' 등 정제
            # 여기서 미리 정제해야 정규식 패턴 매칭이 정확해집니다.
            text = self.final_clean_for_save(text)
            
            # 3. 분할 로직 실행
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
                
            # 4. 결과 저장
            total = len(chunks)
            # zfill 또는 f-string 포맷팅을 사용합니다.
            for i, c in enumerate(chunks, 1):
                # {i:07d}는 숫자 i를 7자리로 만들고, 빈자리는 0으로 채우라는 뜻입니다.
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
