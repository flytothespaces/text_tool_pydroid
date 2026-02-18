from jnius import autoclass
import threading
import time
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk

# ---------------------------------------------------------
# Android Clipboard Access
# ---------------------------------------------------------
Context = autoclass('android.content.Context')
ClipboardManager = autoclass('android.content.ClipboardManager')
PythonActivity = autoclass('org.kivy.android.PythonActivity')

activity = PythonActivity.mActivity
clipboard = activity.getSystemService(Context.CLIPBOARD_SERVICE)


def get_clipboard_text():
    clip = clipboard.getPrimaryClip()
    if clip and clip.getItemCount() > 0:
        item = clip.getItemAt(0)
        return str(item.coerceToText(activity))
    return ""


# ---------------------------------------------------------
# 텍스트 추출 함수
# ---------------------------------------------------------
def extract_section(text, start_pattern, end_pattern):
    """
    사용자 입력 기반 시작/끝 정규식으로 추출
    - 시작 패턴 매칭 실패 시: 0부터 시작
    - 끝 패턴 미입력 또는 매칭 실패 시: 전체 끝까지
    """

    # --------------------
    # 1) 시작 패턴 처리
    # --------------------
    if start_pattern.strip():
        start_match = re.search(start_pattern, text)
        if start_match:
            start_index = start_match.start()
        else:
            start_index = 0  # 패턴 못 찾으면 처음부터
    else:
        start_index = 0

    # --------------------
    # 2) 끝 패턴 처리
    # --------------------
    if end_pattern.strip():
        end_match = re.search(end_pattern, text)
        if end_match:
            # "라인 전체" 포함시키기 위해 그 줄 끝까지 추출
            end_line = text.find("\n", end_match.end())
            if end_line == -1:
                end_index = len(text)
            else:
                end_index = end_line
        else:
            end_index = len(text)
    else:
        end_index = len(text)

    return text[start_index:end_index]


# ---------------------------------------------------------
# GUI 구성
# ---------------------------------------------------------
root = tk.Tk()
root.title("Clipboard Chapter Extractor")
root.geometry("500x750")

# ---------------------------------------------------------
# 상단: 시작/중지 버튼
# ---------------------------------------------------------
frame_top = tk.Frame(root)
frame_top.pack(fill=tk.X, pady=5)

btn_font = ("Arial", 12)

btn_start = tk.Button(frame_top, text="▶ 시작", font=btn_font, height=1)
btn_stop = tk.Button(frame_top, text="■ 중지", font=btn_font, height=1)

btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)


# ---------------------------------------------------------
# 중앙: 텍스트 박스
# ---------------------------------------------------------
frame_mid = tk.Frame(root)
frame_mid.pack(fill=tk.BOTH, expand=True)

text_box = scrolledtext.ScrolledText(frame_mid, wrap=tk.WORD, font=("Arial", 10))
text_box.pack(fill=tk.BOTH, expand=True)

# ---------------------------------------------------------
# 하단: 필터 입력(2개) + 저장 버튼
# ---------------------------------------------------------
frame_bottom = tk.Frame(root)
frame_bottom.pack(fill=tk.X, pady=10)

entry_font = ("Arial", 12)

# ---------------------------------------------------------
# 공용 정규식 옵션
# ---------------------------------------------------------
regex_options = [
    "시작 필터링 문구",  # 라벨 역할
    r"第.+章",
    r"第\d+章",
    r"第[一二三四五六七八九十百千万零〇]+章",
    r"第[\s\S]+?章"
]

regex_options_end = [
    "끝 필터링 문구",  # 라벨 역할
    r"本章完",
    r"本章未完",
    r"完结",
    r"第[\s\S]+?节"
]

# ---------------------------------------------------------
# 콤보 선택 시 entry에 반영
# ---------------------------------------------------------
def apply_start_regex(event):
    v = combo_start.get()
    if v != "시작 필터링 문구":
        start_entry.delete(0, tk.END)
        start_entry.insert(0, v)

def apply_end_regex(event):
    v = combo_end.get()
    if v != "끝 필터링 문구":
        end_entry.delete(0, tk.END)
        end_entry.insert(0, v)

# ---------------------------------------------------------
# 시작 콤보박스
# ---------------------------------------------------------
combo_start = ttk.Combobox(frame_bottom, values=regex_options, state="readonly", font=("Arial", 10), height=6)
combo_start.current(0)
combo_start.pack(fill=tk.X, padx=5, pady=3)
combo_start.bind("<<ComboboxSelected>>", apply_start_regex)

# 시작 입력창
start_entry = tk.Entry(frame_bottom, font=entry_font)
start_entry.pack(fill=tk.X, padx=5, pady=3)
start_entry.insert(0, r"第\d+章")   # 기본값 유지

# ---------------------------------------------------------
# 끝 콤보박스
# ---------------------------------------------------------
combo_end = ttk.Combobox(frame_bottom, values=regex_options_end, state="readonly", font=("Arial", 10), height=6)
combo_end.current(0)
combo_end.pack(fill=tk.X, padx=5, pady=3)
combo_end.bind("<<ComboboxSelected>>", apply_end_regex)

# 끝 입력창
end_entry = tk.Entry(frame_bottom, font=entry_font)
end_entry.pack(fill=tk.X, padx=5, pady=3)
end_entry.insert(0, r"本章完")   # 기본값 유지


# ---------------------------------------------------------
# 파일 저장 기능 (인코딩 안전 버전)
# ---------------------------------------------------------
def save_file():
    txt = text_box.get("1.0", tk.END).strip()
    if not txt:
        messagebox.showwarning("빈 내용", "저장할 내용이 없습니다.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        title="파일 저장"
    )

    if not file_path:
        return

    try:
        # UTF-8 with BOM (완전 호환)
        with open(file_path, "w", encoding="utf-8-sig", errors="replace") as f:
            f.write(txt)

        messagebox.showinfo("저장 완료", f"저장됨:\n{file_path}")

    except Exception as e:
        messagebox.showerror("오류", str(e))




# ---------------------------------------------------------
# 저장 + 키보드 버튼 라인
# ---------------------------------------------------------
frame_save = tk.Frame(frame_bottom)
frame_save.pack(fill=tk.X, pady=10)

# 저장 버튼
btn_save = tk.Button(
    frame_save,
    text="저장",
    font=btn_font,
    width=12,
    height=1,
    command=save_file)
btn_save.pack(side=tk.LEFT, padx=5)

# 키보드 팝업 버튼 기능
def show_keyboard():
    InputMethodManager = autoclass('android.view.inputmethod.InputMethodManager')
    imm = activity.getSystemService(Context.INPUT_METHOD_SERVICE)
    imm.toggleSoftInput(0, 0)

# 키보드 버튼
btn_keyboard = tk.Button(
    frame_save,
    text="⌨",
    font=("Arial", 12),
    width=3,
    command=show_keyboard
)
btn_keyboard.pack(side=tk.RIGHT, padx=5)

# ---------------------------------------------------------
# 클립보드 모니터링 로직
# ---------------------------------------------------------
monitoring = False
last_clip = ""


def monitor_clipboard():
    global monitoring, last_clip

    while monitoring:
        try:
            now = get_clipboard_text()

            if now and now != last_clip:
                start_pat = start_entry.get()
                end_pat = end_entry.get()

                section = extract_section(now, start_pat, end_pat)

                if section and section.strip():
                    last_clip = now
                    root.after(0, lambda t=section: append_text(t))

        except Exception as e:
            print("Error:", e)

        time.sleep(0.2)


def start_monitoring():
    global monitoring
    if not monitoring:
        monitoring = True
        threading.Thread(target=monitor_clipboard, daemon=True).start()
        messagebox.showinfo("시작", "클립보드 모니터링 시작됨")


def stop_monitoring():
    global monitoring
    monitoring = False
    messagebox.showinfo("중지", "클립보드 모니터링 중지됨")


btn_start.configure(command=start_monitoring)
btn_stop.configure(command=stop_monitoring)


# ---------------------------------------------------------
# 텍스트 박스에 추가
# ---------------------------------------------------------
def append_text(t):
    text_box.insert(tk.END, t + "\n\n")
    text_box.see(tk.END)

# ---------------------------------------------------------
# 실행
# ---------------------------------------------------------
root.mainloop()
