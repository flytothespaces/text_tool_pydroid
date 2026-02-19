import os
import re
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserListView
from kivy.properties import StringProperty
from kivy.core.text import LabelBase
from jnius import autoclass

# 한글 폰트 등록
try:
    LabelBase.register(name="Roboto", fn_regular="/storage/emulated/0/Python/fonts/NSCJKR.otf")
except:
    pass

# Android Clipboard 관련 클래스
Context = autoclass('android.content.Context')
ClipData = autoclass('android.content.ClipData') # 복사 기능을 위해 추가
PythonActivity = autoclass('org.kivy.android.PythonActivity')
activity = PythonActivity.mActivity
clipboard = activity.getSystemService(Context.CLIPBOARD_SERVICE)

def get_clipboard_text():
    clip = clipboard.getPrimaryClip()
    if clip and clip.getItemCount() > 0:
        return str(clip.getItemAt(0).coerceToText(activity))
    return ""

def set_clipboard_text(text):
    """안드로이드 시스템 클립보드에 텍스트를 복사함"""
    clip_data = ClipData.newPlainText("copied_text", text)
    clipboard.setPrimaryClip(clip_data)

class ClipboardWatcher(BoxLayout):
    last_content = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=5, **kwargs)
        self.monitoring = False

        # ───────────────────────────────────────────
        # 상단 버튼 (시작, 중지, 초기화)
        # ───────────────────────────────────────────
        top_buttons = BoxLayout(size_hint=(1, 0.1), spacing=5)
        self.btn_start = Button(text="▶ 시작")
        self.btn_stop = Button(text="■ 중지")
        self.btn_reset = Button(text="초기화")
        
        self.btn_start.bind(on_press=self.show_start_confirm)
        self.btn_stop.bind(on_press=lambda x: self.set_monitoring(False))
        self.btn_reset.bind(on_press=self.ask_reset)

        top_buttons.add_widget(self.btn_start)
        top_buttons.add_widget(self.btn_stop)
        top_buttons.add_widget(self.btn_reset)
        self.add_widget(top_buttons)

        # ───────────────────────────────────────────
        # 텍스트 출력 영역
        # ───────────────────────────────────────────
        self.text_area = TextInput(
            multiline=True, 
            readonly=False, 
            font_size='10sp',
            size_hint=(1, 0.55),
            scroll_y=0
        )
        # 터치 시 즉시 새로고침 바인딩
        self.text_area.bind(on_touch_down=lambda inst, touch: self.check_clipboard(0))
        self.add_widget(self.text_area)

        # ───────────────────────────────────────────
        # 필터 설정 UI
        # ───────────────────────────────────────────
        self.start_spinner = Spinner(text="시작 필터 선택", values=["第.+章", r"第\d+章", r"第[\s\S]+?章"], size_hint=(1, 0.07))
        self.start_spinner.bind(text=lambda s, t: setattr(self.start_input, 'text', t))
        self.add_widget(self.start_spinner)

        self.start_input = TextInput(text=r"第\d+章", multiline=False, size_hint=(1, 0.07))
        self.add_widget(self.start_input)

        self.end_spinner = Spinner(text="끝 필터 선택", values=["本章完", "本章未完", "完결"], size_hint=(1, 0.07))
        self.end_spinner.bind(text=lambda s, t: setattr(self.end_input, 'text', t))
        self.add_widget(self.end_spinner)

        self.end_input = TextInput(text="本章完", multiline=False, size_hint=(1, 0.07))
        self.add_widget(self.end_input)
        
        # ───────────────────────────────────────────
        # 하단 버튼 (저장, 복사, 키보드)
        # ───────────────────────────────────────────
        bottom_buttons = BoxLayout(size_hint=(1, 0.1), spacing=5)
        btn_save = Button(text="저장")
        btn_copy_all = Button(text="전체 복사") # 추가된 버튼
        btn_keyboard = Button(text="키보드")
        
        btn_save.bind(on_press=self.open_folder_chooser)
        btn_copy_all.bind(on_press=self.copy_all_text) # 복사 기능 바인딩
        btn_keyboard.bind(on_press=self.show_keyboard)
        
        bottom_buttons.add_widget(btn_save)
        bottom_buttons.add_widget(btn_copy_all) # 추가
        bottom_buttons.add_widget(btn_keyboard)
        self.add_widget(bottom_buttons)

        Clock.schedule_interval(self.check_clipboard, 1.0)

    # 전체 복사 기능
    def copy_all_text(self, instance):
        if self.monitoring:
            # 모니터링 중일 때 경고 팝업
            content = Label(text="모니터링이 켜져 있는 동안에는\n복사 기능을 사용할 수 없습니다.\n먼저 '중지'를 눌러주세요.")
            popup = Popup(title="경고", content=content, size_hint=(0.8, 0.3))
            popup.open()
        else:
            if self.text_area.text.strip():
                set_clipboard_text(self.text_area.text)
                # 복사 완료 알림 (선택 사항)
                Popup(title="알림", content=Label(text="텍스트가 클립보드에 복사되었습니다."), size_hint=(0.7, 0.2)).open()
            else:
                Popup(title="알림", content=Label(text="복사할 내용이 없습니다."), size_hint=(0.7, 0.2)).open()

    # 1. 시작 확인 팝업
    def show_start_confirm(self, instance):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="모니터링을 시작할까요?"))
        btn_layout = BoxLayout(size_hint_y=None, height=100, spacing=10)
        yes_btn = Button(text="확인")
        no_btn = Button(text="취소")
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)
        popup = Popup(title="알림", content=content, size_hint=(0.8, 0.3))
        yes_btn.bind(on_press=lambda x: [self.set_monitoring(True), popup.dismiss()])
        no_btn.bind(on_press=popup.dismiss)
        popup.open()

    # 2. 초기화 확인 팝업
    def ask_reset(self, instance):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="텍스트를 초기화하시겠습니까?"))
        btn_layout = BoxLayout(size_hint_y=None, height=100, spacing=10)
        yes_btn = Button(text="실행")
        no_btn = Button(text="취소")
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)
        popup = Popup(title="확인", content=content, size_hint=(0.8, 0.3))
        yes_btn.bind(on_press=lambda x: [setattr(self.text_area, 'text', ""), popup.dismiss()])
        no_btn.bind(on_press=popup.dismiss)
        popup.open()

    def check_clipboard(self, dt):
        if not self.monitoring and dt != 0:
            return
        try:
            data = get_clipboard_text()
            if data and data != self.last_content:
                self.last_content = data
                res = self.extract_section(data, self.start_input.text, self.end_input.text)
                if res.strip():
                    # 1. 기존 텍스트의 맨 끝에 새로운 텍스트를 결합하여 대입 (항상 끝에 추가됨)
                    self.text_area.text = self.text_area.text.rstrip() + "\n\n" + res + "\n\n"
                    
                    # 2. 커서 위치를 전체 텍스트의 가장 마지막 인덱스로 강제 이동
                    # 이렇게 하면 다음 입력이나 스크롤 위치가 항상 마지막을 가리킵니다.
                    self.text_area.cursor = self.text_area.get_cursor_from_index(len(self.text_area.text))
        except:
            pass

    def set_monitoring(self, flag):
        self.monitoring = flag

    def extract_section(self, text, start_pattern, end_pattern):
        try:
            s_match = re.search(start_pattern, text) if start_pattern.strip() else None
            s_idx = s_match.start() if s_match else 0
            e_match = re.search(end_pattern, text) if end_pattern.strip() else None
            if e_match:
                e_line = text.find("\n", e_match.end())
                e_idx = e_line if e_line != -1 else len(text)
            else:
                e_idx = len(text)
            return text[s_idx:e_idx]
        except:
            return text

    def open_folder_chooser(self, *args):
        layout = BoxLayout(orientation='vertical', spacing=5)
        chooser = FileChooserListView(path="/storage/emulated/0", size_hint=(1, 0.8))
        layout.add_widget(chooser)
        
        btns = BoxLayout(size_hint_y=None, height=120)
        select_btn = Button(text="이 폴더 선택", font_size='18sp')
        cancel_btn = Button(text="취소", font_size='18sp')
        btns.add_widget(select_btn)
        btns.add_widget(cancel_btn)
        layout.add_widget(btns)
        
        popup = Popup(title="경로 선택", content=layout, size_hint=(0.9, 0.9))
        select_btn.bind(on_press=lambda x: self.ask_filename(chooser.path, popup))
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()

    def ask_filename(self, folder_path, folder_popup):
        folder_popup.dismiss()
        layout = BoxLayout(orientation='vertical', spacing=15, padding=20)
        filename_input = TextInput(text="saved_clip.txt", multiline=False, size_hint_y=None, height=110, font_size='20sp')
        layout.add_widget(Label(text="파일명 입력", size_hint_y=None, height=40))
        layout.add_widget(filename_input)
        
        save_btn = Button(text="최종 저장", size_hint_y=None, height=110, font_size='20sp')
        layout.add_widget(save_btn)
        
        popup = Popup(title="저장 설정", content=layout, size_hint=(0.9, 0.45), pos_hint={'top': 0.95})
        save_btn.bind(on_press=lambda x: self.save_file(folder_path, filename_input.text, popup))
        popup.open()

    def save_file(self, folder_path, filename, popup):
        popup.dismiss()
        path = os.path.join(folder_path, filename)
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(self.text_area.text)
            Popup(title="성공", content=Label(text=f"저장완료:\n{path}"), size_hint=(0.8, 0.3)).open()
        except Exception as e:
            Popup(title="오류", content=Label(text=str(e)), size_hint=(0.8, 0.3)).open()

    def show_keyboard(self, *args):
        try:
            imm = activity.getSystemService(Context.INPUT_METHOD_SERVICE)
            imm.toggleSoftInput(0, 0)
        except: pass

class ClipApp(App):
    def build(self):
        return ClipboardWatcher()

if __name__ == "__main__":
    ClipApp().run()
